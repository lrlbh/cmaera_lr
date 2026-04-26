#include "driver/rmt_tx.h"
#include "py/runtime.h"
#include "py/obj.h"
#include "soc/gpio_struct.h"
#include "driver/gpio.h"

// 待处理
// 拆分new,或者优化赋值，让PY可以处理new时部分成功，申请了部分数据的情况
// 提高渐变精度，具体方法见代码注释

static size_t encode_8bit_start(const void *src, size_t src_size, size_t src_offset, size_t symbols_to_encode, rmt_symbol_word_t *hw_symbols, bool *done, void *arg);
static size_t encode_8bit_work(const void *src, size_t src_size, size_t src_offset, size_t symbols_to_encode, rmt_symbol_word_t *hw_symbols, bool *done, void *arg);
static size_t encode_8bit_end(const void *src, size_t src_size, size_t src_offset, size_t symbols_to_encode, rmt_symbol_word_t *hw_symbols, bool *done, void *arg);

typedef struct _rmt_obj_t
{
    rmt_channel_handle_t tx_chan;           // 通道对象
    rmt_encoder_handle_t encoder;           // 编码器对象
    rmt_transmit_config_t tx_config;        // 发送配置
    int free;                               // 发送计数
    uint32_t max_dpi;                       // dac分辨率
    uint32_t symbol_loop;                   // 每字节持续多少符号
    uint32_t encode_symbol_max;             // body中编码多少符号
    int symbol_size;                        // 单个符号长度
    rmt_symbol_word_t *padding_symbol_data; // 填充的数据地址
    int padding_symbol_data_len;            // 填充数据的长度
    int padding_0_xxx;                      // 缓存头和尾的千分比,0~1000
    int padding_symbol_start_len;           // 本次发送,头部实际填充了多少个符号
    int padding_time_us;                    // 0~100的渐变，填充多少时间

    rmt_encode_simple_cb_t next_encode; // 当前回调到哪了

} rmt_obj_t;

// 原始数据
// (rmt_symbol_word_t){
//             .duration0 = 2,
//             .level0 = 1,
//             .duration1 = 2,
//             .level1 = 0,
//         };
// 注意,在copy编码器中
// data_out,必须被赋值，否则会进入胡乱的逻辑，包括当不限于乱传入 data_in 的地址
// 0tisk最好的结果就是让回调不受控的结束
// 1tick == 32767tick
// 所以最小2tick
// 不过 2tick 还是等于 2tick 也就是25ns, 3tick 还是等于 3tick 也就是37.5ns
// 写入的rmt_symbol_word_t 是某些数据似乎会导致编码器提前结束
static size_t IRAM_ATTR encode_8bit(
    const void *data_in,         // 发送时传入的地址
    size_t data_size,            // data长度，发送时传入的长度
    size_t this_len,             // 当前发送到第几个符号了
    size_t data_out_len,         // 本次可编码符号数量
    rmt_symbol_word_t *data_out, // 本次写入地址
    bool *done,                  // 传输完成标记
    void *arg_in)                // 自定义数据
{
    rmt_obj_t *arg = (rmt_obj_t *)arg_in;

    // 可以删除这个if,这只是个保险
    // 因为确切的知道,IDF不满意那些数据,终止回调,比较麻烦,也容易忘记
    if (unlikely(this_len == 0)) // unlikely 此条件很少为真
    {
        arg->next_encode = encode_8bit_start;
    }

    return arg->next_encode(data_in, data_size, this_len,
                            data_out_len, data_out, done, arg);
}

static size_t IRAM_ATTR encode_8bit_start(
    const void *data_in,         // 发送时传入的地址
    size_t data_size,            // data长度，发送时传入的长度
    size_t this_len,             // 当前发送到第几个符号了
    size_t data_out_len,         // 本次可编码符号数量
    rmt_symbol_word_t *data_out, // 本次写入地址
    bool *done,                  // 传输完成标记
    void *arg_in)                // 自定义数据
{
    *done = false;

    // 传入的用户对象
    rmt_obj_t *arg = (rmt_obj_t *)arg_in;

    // 可编码数据不够直接返回
    // 直接 判断 arg->padding_symbol_data_len，可以减少一次计算终止下标
    // 如果第一次数据不够编码，第二次必然返回 >= arg->padding_symbol_data_len
    // 小于arg->padding_symbol_data_len，大于我想编码的量，这种情况不存在，存在也就略微影响速度
    if (data_out_len < arg->padding_symbol_data_len)
    {
        return 0;
    }

    // 计算终止下标
    uint8_t *data = (uint8_t *)data_in;    // 百分比数据位置
    int t = data[0] * 1000 / arg->max_dpi; // 下标的大概千分比
    if (t >= arg->padding_0_xxx)           // 缓存的填充数据不够，那么填充所有数据
    {
        // 缓存的填充数据不够，那么填充所有数据即可
        arg->padding_symbol_start_len = arg->padding_symbol_data_len;
    }
    else
    {
        // 由于填充的数据是2tick开始的，所以此处还需要回退几个下标
        // 不过影响不大，有时间在计算需要回退几个下标
        // 不对，上面方法不划算
        // 回退不如，遍历到下一个 padding_symbol_data 的具体值精度高，遍历几个数据值还可以恢复除法丢失的精度
        arg->padding_symbol_start_len = arg->padding_symbol_data_len * t / arg->padding_0_xxx;
    }

    // 编码
    memcpy(data_out, arg->padding_symbol_data, arg->padding_symbol_start_len * arg->symbol_size);

    // 编码数据时需要使用，访问应该比每次都计算快吧？？？
    arg->encode_symbol_max = data_size * arg->symbol_loop;
    // 指向编码函数
    arg->next_encode = encode_8bit_work;
    return arg->padding_symbol_start_len;
}

static size_t IRAM_ATTR encode_8bit_work(
    const void *data_in,         // 发送时传入的地址
    size_t data_size,            // data长度，发送时传入的长度
    size_t this_len,             // 当前发送到第几个符号了
    size_t data_out_len,         // 本次可编码符号数量
    rmt_symbol_word_t *data_out, // 本次写入地址
    bool *done,                  // 传输完成标记
    void *arg_in)                // 自定义数据
{
    // 自定义参数
    rmt_obj_t *arg = (rmt_obj_t *)arg_in;

    // 当前长度减掉头部
    this_len -= arg->padding_symbol_start_len;

    // 本次可以编码多少符号
    uint32_t send_len = data_out_len - data_out_len % arg->symbol_loop; // 可以编码数据
    if (unlikely(send_len + this_len >= arg->encode_symbol_max))        // 不要超过，剩余数据
    {
        send_len = arg->encode_symbol_max - this_len; // 隐含了最后一个必然是对齐symbol_loop的条件
        arg->next_encode = encode_8bit_end;
    }
    uint32_t char_len = send_len / arg->symbol_loop;

    // 数据当前处理到什么位置
    size_t data_i = this_len / arg->symbol_loop;

    // 需要编码的数据
    char *data = (char *)data_in;

    // esp_rom_printf("char_len %d  ", char_len)

    // 编码数据
    rmt_symbol_word_t temp_data;
    temp_data.level0 = 1;
    temp_data.level1 = 0;
    for (int i = 0; i < char_len; i++)
    {
        temp_data.duration0 = data[data_i + i];
        temp_data.duration1 = arg->max_dpi - temp_data.duration0;
        for (int j = 0; j < arg->symbol_loop; j++)
        {
            (data_out++)->val = temp_data.val;
        }
    }

    *done = false;
    return send_len;
}

static size_t IRAM_ATTR encode_8bit_end(
    const void *data_in,         // 发送时传入的地址
    size_t data_size,            // data长度，发送时传入的长度
    size_t this_len,             // 当前发送到第几个符号了
    size_t data_out_len,         // 本次可编码符号数量
    rmt_symbol_word_t *data_out, // 本次写入地址
    bool *done,                  // 传输完成标记
    void *arg_in)                // 自定义数据
{
    // 自定义参数
    rmt_obj_t *arg = (rmt_obj_t *)arg_in;

    // 防止回调卡在此处，在别处复位没有这里划算
    //      1、不过在这里处理可能丢一次数据，可编码空间足够还是返回0，此次传输会被IDF关闭
    //      2、如果在start中死亡，那么下次还是在start上。
    //      3、如果上次在body中死亡，那么下次只是会丢掉头部，前提是在此处重置 symbol_max
    //          a、不对如果在body中死亡那么，也需要重置 symbol_max，在body中需要重置，所有优势都没了，还是在切换状态处强制重置算了
    //      4、如果在end中死亡才会出现问题，不过可以通过this_len==0返回start状态
    // if (this_len == 0)
    // {
    //     *done = false;
    //     arg->next_encode = encode_8bit_start;
    //     return 0;
    // }

    // 尾部BUG,需要进行一次空调用
    if (this_len > arg->encode_symbol_max + arg->padding_symbol_start_len)
    {
        *done = true;
        arg->next_encode = encode_8bit_start;
        return 0;
    }

    // 可编码器空间不够
    *done = false;
    if (data_out_len < arg->padding_symbol_data_len)
    {
        return 0;
    }

    // 需要编码的长度
    uint8_t *data = (uint8_t *)data_in;                // 百分比数据位置
    int t = data[data_size - 1] * 1000 / arg->max_dpi; // 下标的大概千分比
    int end;
    if (t >= arg->padding_0_xxx)
    {

        end = arg->padding_symbol_data_len;
    }
    else
    {
        end = arg->padding_symbol_data_len * t / arg->padding_0_xxx; // 终止下标
    }

    // 编码
    rmt_symbol_word_t *src = (rmt_symbol_word_t *)arg->padding_symbol_data;
    rmt_symbol_word_t *dest = (rmt_symbol_word_t *)data_out;
    for (size_t i = 0; i < end; i++)
    {
        // 从源的末尾取，存到目标的开头
        dest[i] = src[end - 1 - i];
    }

    return end;
}

// 发送完成的回调函数
static bool IRAM_ATTR rmt_on_transmit_done(rmt_channel_handle_t tx_chan, const rmt_tx_done_event_data_t *edata, void *user_ctx)
{
    // 计数，用于用户逻辑中回收内存
    rmt_obj_t *this = (rmt_obj_t *)user_ctx;
    ++this->free;
    return false;
}

// 创建通道
// 此函数需要拆分,否则不方便处理new失败时,需要释放部分资源的情况
static mp_obj_t new_rmt(size_t n_args, const mp_obj_t *args)
{

    // 获取python传入变量
    int gpio = mp_obj_get_int(args[0]);              // rmt引脚
    int queue_len = mp_obj_get_int(args[1]);         // 发送队列长度
    int mem_block_symbols = mp_obj_get_int(args[2]); // GPIO缓存符号数
    int dma = mp_obj_get_int(args[3]);               // 是否dma
    int intr_priority = mp_obj_get_int(args[4]);     // 中断优先级
    int is_od = mp_obj_get_int(args[5]);             // false 时推挽
    int encode_id = mp_obj_get_int(args[6]);         // 选择编码器
    int max_dpi = mp_obj_get_int(args[7]);           // dac分辨率
    int symbol_loop = mp_obj_get_int(args[8]);       // 每字节等于多少符号
    int padding_time_us = mp_obj_get_int(args[9]);   // 填充时间
    int padding_0_xxx = mp_obj_get_int(args[10]);    // 填充千分比

    // 返回对象
    rmt_obj_t *rmt = malloc(sizeof(rmt_obj_t));
    if (!rmt)
    {
        mp_raise_msg(&mp_type_Exception, MP_ERROR_TEXT("malloc_ret_p_error"));
    }
    rmt->free = 0;
    rmt->max_dpi = max_dpi;
    rmt->symbol_loop = symbol_loop;
    rmt->symbol_size = sizeof(rmt_symbol_word_t);
    rmt->padding_time_us = padding_time_us * 1000;
    rmt->padding_0_xxx = padding_0_xxx;
    rmt->padding_symbol_data_len = rmt->max_dpi * 12.5; // 单个周期时间
    rmt->padding_symbol_data_len =                      // 需要周期数
        rmt->padding_time_us / rmt->padding_symbol_data_len *
        rmt->padding_0_xxx / 1000;
    rmt->padding_symbol_data =
        heap_caps_calloc_prefer(                   // 申请填充空间
            rmt->padding_symbol_data_len,          // 元素个数
            rmt->symbol_size,                      // 元素大小
            2,                                     // 备选方案个数
            MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT, // 内部SRAM,8bit访问
            MALLOC_CAP_SPIRAM);                    // 外部PSRAM
    // 每个周期递增值
    int tt = (rmt->max_dpi - 3);            // 修正max，为了保证填充数据大于2tick
    tt = tt * rmt->padding_0_xxx;           // 填充到多少占空比
    tt = tt / rmt->padding_symbol_data_len; // 平均每个需要填充多少值

    for (int i = 0; i < rmt->padding_symbol_data_len; i++) // 填充缓存
    {
        rmt->padding_symbol_data[i].duration0 = tt * i / 1000 + 2;
        rmt->padding_symbol_data[i].level0 = 1;
        rmt->padding_symbol_data[i].duration1 = rmt->max_dpi - rmt->padding_symbol_data[i].duration0;
        rmt->padding_symbol_data[i].level1 = 0;
    }
    rmt->next_encode = encode_8bit_start; // 回调函数起点

    // 通道配置
    rmt_tx_channel_config_t tx_chan_config = {
        .clk_src = RMT_CLK_SRC_DEFAULT,         // 选择时钟源：80MHz APB
        .gpio_num = gpio,                       // 选择输出引脚
        .mem_block_symbols = mem_block_symbols, // 通道中保存多少个 rmt_symbol_word_t
                                                // dma下最大2046
                                                // 最后一次编码的 “字节” 不能小于此数，否则多出的会被截断
        .resolution_hz = 80000000,              // 时钟源频率   1 tick = 12.5ns
        .trans_queue_depth = queue_len,         // 传输队列深度，允许同时排队多组波形
        .flags.with_dma = dma,                  // 开启 DMA 模式
        .intr_priority = intr_priority,         // 中断优先级，传0驱动自动分配为低优先级
        .flags.io_od_mode = is_od               // 0推挽，1开漏
    };

    // 创建通道
    esp_err_t err = rmt_new_tx_channel(&tx_chan_config, &rmt->tx_chan);
    if (err != ESP_OK)
    {
        mp_raise_msg_varg(
            &mp_type_Exception, MP_ERROR_TEXT("creaet_chan_error: %d"), err);
    }

    // 使能通道
    err = rmt_enable(rmt->tx_chan);
    if (err != ESP_OK)
    {
        mp_raise_msg_varg(
            &mp_type_Exception, MP_ERROR_TEXT("en_chan_error: %d"), err);
    }

    // 创建编码器
    if (encode_id == 1)
    {
        rmt_copy_encoder_config_t copy_encoder_config = {};
        err = rmt_new_copy_encoder(&copy_encoder_config, &rmt->encoder);
    }
    else if (encode_id == 2)
    {

        rmt_simple_encoder_config_t simple_encoder_config = {
            .callback = encode_8bit,                        // 编码器回调
            .arg = rmt,                                     // 传入数据
            .min_chunk_size = rmt->padding_symbol_data_len, // 多少数据不编码，回调死亡
        };
        err = rmt_new_simple_encoder(&simple_encoder_config, &rmt->encoder);
    }
    else // 默认8bit编码器
    {
        rmt_simple_encoder_config_t simple_encoder_config = {
            .callback = encode_8bit,                        // 编码器回调
            .arg = rmt,                                     // 传入数据
            .min_chunk_size = rmt->padding_symbol_data_len, // 多少数据不编码，回调死亡
        };
        err = rmt_new_simple_encoder(&simple_encoder_config, &rmt->encoder);
    }

    if (err != ESP_OK)
    {
        mp_raise_msg_varg(
            &mp_type_Exception, MP_ERROR_TEXT("creaet_encoder_error: %d"), err);
    }

    // 发送配置
    rmt->tx_config = (rmt_transmit_config_t){
        .loop_count = 0,              // 不循环，发送0次,迷之参数
        .flags.eot_level = 0,         // 发送完成后，引脚配置为低电平
        .flags.queue_nonblocking = 1, // 队列满时返回错误
    };

    // 发送完成的回调函数
    rmt_tx_event_callbacks_t cbs = {
        .on_trans_done = rmt_on_transmit_done,
    };
    err = rmt_tx_register_event_callbacks(rmt->tx_chan, &cbs, rmt);
    if (err != ESP_OK)
    {
        mp_raise_msg_varg(
            &mp_type_Exception,
            MP_ERROR_TEXT("add_cbs_error: %d"), err);
    }

    // 返回数据
    return mp_obj_new_int_from_uint((mp_uint_t)rmt);
}

// 发送数据
static mp_obj_t rmt_send(
    mp_obj_t rmt_in, mp_obj_t data_p_in, mp_obj_t data_len_in)
{
    rmt_obj_t *rmt = (rmt_obj_t *)mp_obj_get_uint(rmt_in);
    mp_buffer_info_t data;
    mp_get_buffer_raise(data_p_in, &data, MP_BUFFER_RW);
    size_t data_len = mp_obj_get_int(data_len_in);

    // 发送
    esp_err_t err = rmt_transmit(
        rmt->tx_chan,
        rmt->encoder,
        data.buf,
        data_len,
        &rmt->tx_config);
    if (err != ESP_OK)
    {
        mp_raise_msg_varg(&mp_type_Exception, MP_ERROR_TEXT("sen_error: %d"), err);
    }

    return mp_const_none;
}

// 获取单个数据大小
static mp_obj_t rmt_get_symbol_size()
{
    return mp_obj_new_int(sizeof(rmt_symbol_word_t));
}

// 停止通道
static mp_obj_t rmt_stop_channel(mp_obj_t rmt_in)
{
    rmt_obj_t *rmt = (rmt_obj_t *)mp_obj_get_uint(rmt_in);

    // 建议先等待当前传输完成，防止强制停止导致的电平错误
    // 只影响发送中的数据正确，不影响资源释放，-1阻塞等待
    // rmt_tx_wait_all_done(rmt->tx_chan, -1);

    esp_err_t err = rmt_disable(rmt->tx_chan);
    if (err != ESP_OK)
    {
        mp_raise_msg_varg(
            &mp_type_Exception,
            MP_ERROR_TEXT("rmt_free,stop_channel_error: %d"), err);
    }
    return mp_const_none;
}

// 释放编码器
static mp_obj_t rmt_delete_encoder(mp_obj_t rmt_in)
{
    rmt_obj_t *rmt = (rmt_obj_t *)mp_obj_get_uint(rmt_in);

    if (rmt->encoder)
    {
        esp_err_t err = rmt_del_encoder(rmt->encoder);
        if (err != ESP_OK)
        {
            mp_raise_msg_varg(
                &mp_type_Exception,
                MP_ERROR_TEXT("rmt_free,delete_encoder_error: %d"), err);
        }
        rmt->encoder = NULL; // 避免重复删除
    }
    return mp_const_none;
}

// 释放通道
static mp_obj_t rmt_delete_channel(mp_obj_t rmt_in)
{
    rmt_obj_t *rmt = (rmt_obj_t *)mp_obj_get_uint(rmt_in);

    // 1. 删除通道（会自动注销之前注册的 callback）
    if (rmt->tx_chan)
    {
        esp_err_t err = rmt_del_channel(rmt->tx_chan);
        if (err != ESP_OK)
        {
            mp_raise_msg_varg(
                &mp_type_Exception,
                MP_ERROR_TEXT("rmt_free,delete_channel_error: %d"), err);
        }
        rmt->tx_chan = NULL;
    }

    return mp_const_none;
}

// 获取int值
static mp_obj_t rmt_get_free(mp_obj_t rmt_in)
{
    rmt_obj_t *rmt = (rmt_obj_t *)mp_obj_get_uint(rmt_in);
    return mp_obj_new_int(rmt->free);
}

// 设置int值
static mp_obj_t rmt_sub_free(mp_obj_t rmt_in, mp_obj_t val_in)
{
    rmt_obj_t *rmt = (rmt_obj_t *)mp_obj_get_uint(rmt_in);
    rmt->free -= mp_obj_get_int(val_in);
    return mp_const_none;
}

// 在下方提供注册到mpy的代码， 模块名: rmt_lr
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须

// --- 宏定义与函数绑定 ---

// 1. 固定参数函数绑定
// rmt_send(rmt_in, data_p_in, data_len_in) -> 3个参数
MP_DEFINE_CONST_FUN_OBJ_3(rmt_send_obj, rmt_send);

// rmt_get_symbol_size() -> 0个参数
MP_DEFINE_CONST_FUN_OBJ_0(rmt_get_symbol_size_obj, rmt_get_symbol_size);

// rmt_stop_channel(rmt_in) -> 1个参数
MP_DEFINE_CONST_FUN_OBJ_1(rmt_stop_channel_obj, rmt_stop_channel);

// rmt_delete_encoder(rmt_in) -> 1个参数
MP_DEFINE_CONST_FUN_OBJ_1(rmt_delete_encoder_obj, rmt_delete_encoder);

// rmt_delete_channel(rmt_in) -> 1个参数
MP_DEFINE_CONST_FUN_OBJ_1(rmt_delete_channel_obj, rmt_delete_channel);

// rmt_get_free(rmt_in) -> 1个参数
MP_DEFINE_CONST_FUN_OBJ_1(rmt_get_free_obj, rmt_get_free);

// rmt_sub_free(rmt_in, val_in) -> 2个参数
MP_DEFINE_CONST_FUN_OBJ_2(rmt_sub_free_obj, rmt_sub_free);

// 2. 变长参数函数绑定
// new_rmt(n_args, args) -> 11个参数，使用 VAR_BETWEEN
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(new_rmt_obj, 11, 11, new_rmt);

// --- 模块入口表 ---

static const mp_rom_map_elem_t rmt_lr_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_rmt_lr)},

    // 必须 C 函数名 == PY 函数名
    {MP_ROM_QSTR(MP_QSTR_new_rmt), MP_ROM_PTR(&new_rmt_obj)},
    {MP_ROM_QSTR(MP_QSTR_rmt_send), MP_ROM_PTR(&rmt_send_obj)},
    {MP_ROM_QSTR(MP_QSTR_rmt_get_symbol_size), MP_ROM_PTR(&rmt_get_symbol_size_obj)},
    {MP_ROM_QSTR(MP_QSTR_rmt_stop_channel), MP_ROM_PTR(&rmt_stop_channel_obj)},
    {MP_ROM_QSTR(MP_QSTR_rmt_delete_encoder), MP_ROM_PTR(&rmt_delete_encoder_obj)},
    {MP_ROM_QSTR(MP_QSTR_rmt_delete_channel), MP_ROM_PTR(&rmt_delete_channel_obj)},
    {MP_ROM_QSTR(MP_QSTR_rmt_get_free), MP_ROM_PTR(&rmt_get_free_obj)},
    {MP_ROM_QSTR(MP_QSTR_rmt_sub_free), MP_ROM_PTR(&rmt_sub_free_obj)},
};

// 注册 globals table
static MP_DEFINE_CONST_DICT(rmt_lr_module_globals, rmt_lr_module_globals_table);

// --- 定义模块对象 ---

const mp_obj_module_t rmt_lr_user_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&rmt_lr_module_globals,
};

// 注册模块到 MicroPython 核心 (需要配置 micropython.mk 或 mpconfigport.h)
MP_REGISTER_MODULE(MP_QSTR_rmt_lr, rmt_lr_user_module);