#include "driver/rmt_tx.h"
#include "py/runtime.h"
#include "py/obj.h"

typedef struct _rmt_obj_t
{
    rmt_channel_handle_t tx_chan;
    rmt_encoder_handle_t copy_encoder;
    rmt_transmit_config_t tx_config;
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

// 发送完成的回调函数
static bool rmt_on_transmit_done(rmt_channel_handle_t tx_chan, const rmt_tx_done_event_data_t *edata, void *user_ctx)
{
    // if (edata->num_symbols ==)

    rmt_obj_t *this = (rmt_obj_t *)user_ctx;

    // 搞不懂edata为什么没有携带发送完的地址，或者我没找到？
    // 这里只能计数，然后在外部确保释放正确的数据了
    this->free++;

    return false;
}

// 创建通道
static mp_obj_t new_rmt(size_t n_args, const mp_obj_t *args)
{

    int gpio_t = mp_obj_get_int(args[0]);
    int data_num_t = mp_obj_get_int(args[1]);
    int data_len_t = mp_obj_get_int(args[2]);
    int mem_block_symbols_t = mp_obj_get_int(args[3]);
    int dma = mp_obj_get_int(args[4]);

    // 通道配置
    rmt_tx_channel_config_t tx_chan_config = {
        .clk_src = RMT_CLK_SRC_DEFAULT,           // 选择时钟源：80MHz APB
        .gpio_num = gpio_t,                       // 选择输出引脚
        .mem_block_symbols = mem_block_symbols_t, // 通道中保存多少个 rmt_symbol_word_t
        .resolution_hz = 80000000,                // 时钟源频率   1 tick = 12.5ns
        .trans_queue_depth = data_len_t,          // 传输队列深度，允许同时排队多组波形
        .flags.with_dma = dma,                    // 开启 DMA 模式
    };

    // 创建通道
    rmt_channel_handle_t tx_chan;
    esp_err_t err = rmt_new_tx_channel(&tx_chan_config, &tx_chan);
    if (err != ESP_OK)
    {
        mp_raise_msg_varg(
            &mp_type_Exception, MP_ERROR_TEXT("creaet_chan_error: %d"), err);
    }

    // 使能通道
    err = rmt_enable(tx_chan);
    if (err != ESP_OK)
    {
        mp_raise_msg_varg(
            &mp_type_Exception, MP_ERROR_TEXT("en_chan_error: %d"), err);
    }

    // 创建 Copy Encoder     ？？
    rmt_encoder_handle_t copy_encoder;
    rmt_copy_encoder_config_t copy_encoder_config = {};
    err = rmt_new_copy_encoder(&copy_encoder_config, &copy_encoder);
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
        void *mem_lr = heap_caps_malloc(buffer_size, MALLOC_CAP_DMA);
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

    // 数据放入堆中返回
    rmt_obj_t *rmt = malloc(sizeof(rmt_obj_t));
    // 千万别让mpy管理内存，它似乎会移动内存地址
    // rmt_obj_t *rmt = m_new_obj(rmt_obj_t);
    if (!rmt)
    {
        mp_raise_msg(&mp_type_Exception, MP_ERROR_TEXT("malloc_ret_p_error"));
    }
    rmt->tx_chan = tx_chan;
    rmt->copy_encoder = copy_encoder;
    rmt->tx_config = (rmt_transmit_config_t){
        .loop_count = 0,
        .flags.eot_level = 0,
    };
    rmt->free = 0;

    // 发送完成的回调函数
    rmt_tx_event_callbacks_t cbs = {
        .on_trans_done = rmt_on_transmit_done,
    };
    err = rmt_tx_register_event_callbacks(tx_chan, &cbs, rmt);
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
        rmt->copy_encoder,
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

    if (rmt->copy_encoder)
    {
        esp_err_t err = rmt_del_encoder(rmt->copy_encoder);
        if (err != ESP_OK)
        {
            mp_raise_msg_varg(
                &mp_type_Exception,
                MP_ERROR_TEXT("rmt_free,delete_encoder_error: %d"), err);
        }
        rmt->copy_encoder = NULL; // 避免重复删除
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