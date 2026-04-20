#include "driver/rmt_tx.h"
#include "py/runtime.h"
#include "py/obj.h"
#include "soc/gpio_struct.h"
#include "driver/gpio.h"
typedef struct _rmt_obj_t
{
    rmt_channel_handle_t tx_chan;
    rmt_encoder_handle_t encoder;
    rmt_transmit_config_t tx_config;
    int gpio;
    int free;
} rmt_obj_t;

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

// static size_t IRAM_ATTR test_enc(
//     const void *data_in,         // 内外部共享内存地址
//     size_t data_size,            // 内外部共享内存长度,单位字节
//     size_t this_len,             // 当前发送到哪里了
//     size_t data_out_len,         // 本次可以写入最大长度
//     rmt_symbol_word_t *data_out, // 本次写入地址
//     bool *done,                  // 传输完成标记,千万千万不能设置为true
//                                  // 否则即使发送参数是死循环,也不会进入回调了
//     void *arg_in)                // 自定义数据
// {

//     // if (this_len < 192)
//     // {
//     //     data_out_len = 192;
//     // }

//     rmt_obj_t *arg = (rmt_obj_t *)arg_in;

//     rmt_symbol_word_t *data = (rmt_symbol_word_t *)data_in;

//     memcpy(data_out, data + this_len, data_out_len * 4);

//     if (this_len * 4 >= data_size)
//     {
//         *done = true;
//     }
//     else
//     {
//         *done = false;
//     }

//     // if (this_len == 0)
//     // {
//     //     // 设置引脚为PP
//     //     GPIO.pin[arg->gpio].pad_driver = 0;
//     // }

//     // 发送参数里面死循环是假的，不会生效，所以返回true,回调将再也不会被执行
//     // 如果在编码器完数据后还试图返回false，那么IDF将奔溃重启
//     // 所以在编码器中也无法实现RMT连续模式
//     return data_out_len;
// }

// 发送完成的回调函数
static bool IRAM_ATTR rmt_on_transmit_done(rmt_channel_handle_t tx_chan, const rmt_tx_done_event_data_t *edata, void *user_ctx)
{
    // if (edata->num_symbols ==)

    // 获取自定义数据
    rmt_obj_t *this = (rmt_obj_t *)user_ctx;

    // 设置引脚为OD
    // GPIO.pin[this->gpio].pad_driver = 1;
    // 设置高阻
    // gpio_config_t io_conf = {
    //     .pin_bit_mask = (1ULL << this->gpio),
    //     .mode = GPIO_MODE_INPUT,               // 禁用输出驱动
    //     .pull_up_en = GPIO_PULLUP_DISABLE,     // 禁用上拉
    //     .pull_down_en = GPIO_PULLDOWN_DISABLE, // 禁用下拉
    //     .intr_type = GPIO_INTR_DISABLE};
    // gpio_config(&io_conf);

    // 搞不懂edata为什么没有携带发送完的地址，或者我没找到？
    // 这里只能计数，然后在外部确保释放正确的数据了
    ++this->free;

    return false;
}

// 创建通道
static mp_obj_t new_rmt(size_t n_args, const mp_obj_t *args)
{

    int gpio_t = mp_obj_get_int(args[0]);
    int data_len_t = mp_obj_get_int(args[1]);
    int data_num_t = mp_obj_get_int(args[2]);
    int mem_block_symbols_t = mp_obj_get_int(args[3]);
    int dma = mp_obj_get_int(args[4]);

    // 返回对象
    // 千万别让mpy管理内存，它似乎会移动整理内存地址
    // rmt_obj_t *rmt = m_new_obj(rmt_obj_t);
    rmt_obj_t *rmt = malloc(sizeof(rmt_obj_t));
    rmt->free = 0;
    rmt->gpio = gpio_t;
    if (!rmt)
    {
        mp_raise_msg(&mp_type_Exception, MP_ERROR_TEXT("malloc_ret_p_error"));
    }

    // 通道配置
    rmt_tx_channel_config_t tx_chan_config = {
        .clk_src = RMT_CLK_SRC_DEFAULT,           // 选择时钟源：80MHz APB
        .gpio_num = gpio_t,                       // 选择输出引脚
        .mem_block_symbols = mem_block_symbols_t, // 通道中保存多少个 rmt_symbol_word_t
        .resolution_hz = 80000000,                // 时钟源频率   1 tick = 12.5ns
        .trans_queue_depth = data_num_t,          // 传输队列深度，允许同时排队多组波形
        .flags.with_dma = dma,                    // 开启 DMA 模式
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
    // rmt_simple_encoder_config_t simple_encoder_config = {
    //     .callback = test_enc, // 编码器回调
    //     .arg = rmt,           // 传入数据
    //     .min_chunk_size = 32, /*    不知道这傻逼参数要干什么
    //                                 看样子是说有最少多少空位才触发回调
    //                                 然而，非dma情况下每个通道只有48个空间，它默认64？？？
    //                                 如果没有通道合并，默认就是BUG，回调不会被触????
    //                                 翻译了1个小时也不知道想表达什么
    //                                 傻逼东西    */
    // };
    // err = rmt_new_simple_encoder(&simple_encoder_config, &rmt->encoder);
    rmt_copy_encoder_config_t copy_encoder_config = {};
    err = rmt_new_copy_encoder(&copy_encoder_config, &rmt->encoder);
    if (err != ESP_OK)
    {
        mp_raise_msg_varg(
            &mp_type_Exception, MP_ERROR_TEXT("creaet_copy_encoder_error: %d"), err);
    }

    // 分配内存，避免数据拷贝
    mp_obj_t list_out = mp_obj_new_list(0, NULL);
    for (int i = 0; i < data_num_t; i++)
    {
        // 申请内存
        size_t buffer_size = sizeof(rmt_symbol_word_t) * data_len_t;
        // void *mem_lr = heap_caps_malloc(buffer_size, MALLOC_CAP_DMA );
        void *mem_lr = heap_caps_malloc(buffer_size, MALLOC_CAP_SPIRAM);
        if (!mem_lr)
        {
            mp_raise_msg_varg(
                &mp_type_Exception,
                MP_ERROR_TEXT("malloc_mem_%d_error: %d"), i + 1, err);
        }
        // 内存地址放入bytearray
        mp_obj_t ba = mp_obj_new_bytearray_by_ref(buffer_size, mem_lr);
        // bytearray 放入list
        mp_obj_list_append(list_out, ba);
    }

    // 发送配置
    rmt->tx_config = (rmt_transmit_config_t){
        .loop_count = 0, // 循环配置，不过是假的
                         // dma下不会生效,非dma下也行为怪异
                         // 又似乎是受到编码器影响
                         // 所以必须为0

        .flags.eot_level = 0, // 发送完成后，引脚配置为低电平
                              // 如果发送前设置引脚模式的话
                              // 可以设置为高，切换od和pp糊弄一下间隔
                              // 以及在IDF源码中尝试了，失败
                              // 保持电平不是代码设置的，切入时机要么早了，要么晚了

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
    mp_obj_t tuple[2] = {
        mp_obj_new_int_from_uint((mp_uint_t)rmt),
        list_out};
    return mp_obj_new_tuple(2, tuple);
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

// 定义函数引用
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(new_rmt_obj, 5, 5, new_rmt);
static MP_DEFINE_CONST_FUN_OBJ_3(rmt_send_obj, rmt_send);
static MP_DEFINE_CONST_FUN_OBJ_0(rmt_get_symbol_size_obj, rmt_get_symbol_size);
static MP_DEFINE_CONST_FUN_OBJ_1(rmt_stop_channel_obj, rmt_stop_channel);
static MP_DEFINE_CONST_FUN_OBJ_1(rmt_delete_encoder_obj, rmt_delete_encoder);
static MP_DEFINE_CONST_FUN_OBJ_1(rmt_delete_channel_obj, rmt_delete_channel);
static MP_DEFINE_CONST_FUN_OBJ_1(rmt_get_free_obj, rmt_get_free);
static MP_DEFINE_CONST_FUN_OBJ_2(rmt_sub_free_obj, rmt_sub_free);

// 映射 Python 函数名到 C 函数
static const mp_rom_map_elem_t rmt_lr_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_rmt_lr)},
    {MP_ROM_QSTR(MP_QSTR_new), MP_ROM_PTR(&new_rmt_obj)},
    {MP_ROM_QSTR(MP_QSTR_send), MP_ROM_PTR(&rmt_send_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_free), MP_ROM_PTR(&rmt_get_free_obj)}, // 新增
    {MP_ROM_QSTR(MP_QSTR_sub_free), MP_ROM_PTR(&rmt_sub_free_obj)}, // 新增
    {MP_ROM_QSTR(MP_QSTR_get_symbol_size), MP_ROM_PTR(&rmt_get_symbol_size_obj)},
    {MP_ROM_QSTR(MP_QSTR_stop), MP_ROM_PTR(&rmt_stop_channel_obj)},
    {MP_ROM_QSTR(MP_QSTR_del_encoder), MP_ROM_PTR(&rmt_delete_encoder_obj)},
    {MP_ROM_QSTR(MP_QSTR_del_channel), MP_ROM_PTR(&rmt_delete_channel_obj)},
};
static MP_DEFINE_CONST_DICT(rmt_lr_module_globals, rmt_lr_module_globals_table);

// 定义模块
const mp_obj_module_t rmt_lr_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&rmt_lr_module_globals,
};

// 注册模块 (模块名: rmt_lr)
MP_REGISTER_MODULE(MP_QSTR_rmt_lr, rmt_lr_user_cmodule);