#include "driver/rmt_tx.h"
#include "py/runtime.h"
#include "py/obj.h"
#include "soc/gpio_struct.h"
#include "driver/gpio.h"

// 待处理
// dma 大小，是否会影响别的外设
// 不从中心值渐变，从第一个和最后一个字节渐变
// 晕了，渐变效果和需要几个音频数据无关，和需要多少多少时间有关
// 渐变插入是否可以不在回调函数中，在编码器创建或者销毁时
typedef struct _rmt_obj_t
{
    rmt_channel_handle_t tx_chan;    // 通道对象
    rmt_encoder_handle_t encoder;    // 编码器对象
    rmt_transmit_config_t tx_config; // 发送配置
    int free;                        // 发送计数
    uint32_t max;                    // dac分辨率
    uint32_t symbol_loop;            // 每字节持续多少符号
    uint32_t zero;                   // 大概中心值
    uint32_t symbol_max;             // 渐变头 + 数据的符号数量
    int start_symbol;                // 渐变头 符号数量
    int end_symbol;                  // 渐变 符号数量
    int srart_ttt;                   // 头 渐变递增
    int end_ttt;                     // 尾 渐变递增
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

    // 自定义参数
    rmt_obj_t *arg = (rmt_obj_t *)arg_in;

    // 头渐变
    if (this_len == 0)
    {
        // 数据不够不编码
        *done = false;
        if (data_out_len < arg->start_symbol)
        {
            return 0;
        }
        // 需要编码器的的长度
        arg->symbol_max = data_size * arg->symbol_loop + arg->start_symbol;
        for (int i = 0; i < arg->start_symbol; i++)
        {
            data_out[i].level0 = 1;
            data_out[i].level1 = 0;
            data_out[i].duration0 = i * arg->srart_ttt / 1000 + 2;
            data_out[i].duration1 = arg->max - data_out[i].duration0;
        }
        return arg->start_symbol;
    }

    // 尾渐变
    if (this_len == arg->symbol_max)
    {
        *done = false;
        if (data_out_len < arg->end_symbol)
        {

            return 0;
        }

        // esp_rom_printf(" %d  %d  \n", arg->end_symbol, data_out_len);
        for (int i = 0; i < arg->end_symbol; i++)
        {
            data_out[i].level0 = 1;
            data_out[i].level1 = 0;
            data_out[i].duration0 = arg->zero - (i * arg->end_ttt / 1000) + 2;
            data_out[i].duration1 = arg->max - data_out[i].duration0;
        }

        // *done = true;
        return arg->end_symbol;
    }

    // 尾部BUG
    if (this_len > arg->symbol_max)
    {
        *done = true;
        return 0;
    }

    // 本次可以编码多少符号
    uint32_t send_len = data_out_len - data_out_len % arg->symbol_loop; // 可以编码数据
    if (send_len + this_len > arg->symbol_max)                          // 不要超过，剩余数据
    {
        send_len = arg->symbol_max - this_len;
    }
    uint32_t char_len = send_len / arg->symbol_loop;

    // 数据当前处理到什么位置
    size_t data_i = this_len / arg->symbol_loop - (arg->start_symbol / arg->symbol_loop);

    // 需要编码的数据
    char *data = (char *)data_in;

    // esp_rom_printf("char_len %d  ", char_len)

    // 编码数据
    rmt_symbol_word_t temp_data;
    temp_data.level0 = 1;
    temp_data.level1 = 0;
    for (int i = 0; i < char_len; i++)
    {
        temp_data.duration1 = arg->max - data[data_i + i];
        temp_data.duration0 = arg->max - temp_data.duration1;
        for (int j = 0; j < arg->symbol_loop; j++)
        {
            (data_out++)->val = temp_data.val;
        }
    }

    *done = false;
    return send_len;
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
static mp_obj_t new_rmt(size_t n_args, const mp_obj_t *args)
{

    // 获取python传入变量
    int gpio = mp_obj_get_int(args[0]); // rmt引脚
    // int data_len_t = mp_obj_get_int(args[1]);
    int queue_len = mp_obj_get_int(args[1]);         // 发送队列长度
    int mem_block_symbols = mp_obj_get_int(args[2]); // GPIO缓存
    int dma = mp_obj_get_int(args[3]);               // 是否dma
    int intr_priority = mp_obj_get_int(args[4]);     // 中断优先级
    int is_od = mp_obj_get_int(args[5]);             // false 时推挽
    int encode_id = mp_obj_get_int(args[6]);         // 选择编码器
    int dac_max = mp_obj_get_int(args[7]);           // dac分辨率
    int symbol_loop = mp_obj_get_int(args[8]);       // 每字节等于多少符号
    int hed_symbol = mp_obj_get_int(args[9]);        // 头填充多少个dac数据
    int end_symbol = mp_obj_get_int(args[10]);       // 尾填充多少个dac数据

    // 返回对象
    rmt_obj_t *rmt = malloc(sizeof(rmt_obj_t));
    rmt->free = 0;
    rmt->symbol_loop = symbol_loop;
    rmt->max = dac_max;
    rmt->zero = dac_max / 2;
    rmt->start_symbol = rmt->symbol_loop * hed_symbol;
    rmt->end_symbol = rmt->symbol_loop * end_symbol;
    rmt->srart_ttt = rmt->zero * 1000 / rmt->start_symbol;
    rmt->end_ttt = rmt->zero * 1000 / rmt->end_symbol;

    int ttt = rmt->srart_ttt;
    if (ttt < rmt->end_symbol)
    {
        ttt = rmt->end_symbol;
    }

    if (!rmt)
    {
        mp_raise_msg(&mp_type_Exception, MP_ERROR_TEXT("malloc_ret_p_error"));
    }

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
    else if (encode_id == 2) // 需要在else中执行,避免未定义编码器情况
    {

        rmt_simple_encoder_config_t simple_encoder_config = {
            .callback = encode_8bit, // 编码器回调
            .arg = rmt,              // 传入数据
            .min_chunk_size = ttt,   // 多少数据不编码，回调死亡
        };
        err = rmt_new_simple_encoder(&simple_encoder_config, &rmt->encoder);
    }
    if (err != ESP_OK)
    {
        mp_raise_msg_varg(
            &mp_type_Exception, MP_ERROR_TEXT("creaet_copy_encoder_error: %d"), err);
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