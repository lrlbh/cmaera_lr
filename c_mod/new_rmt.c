/*
    万万没想到IDF中关于RMT的发送不是连续的
    这里只能在重新实现一次RMT的c_mod了
*/

#include "driver/rmt_tx.h"
#include "py/runtime.h"
#include "py/obj.h"

typedef struct _rmt_obj_t
{
    rmt_channel_handle_t tx_chan;
    rmt_encoder_handle_t copy_encoder;
    rmt_transmit_config_t tx_config;
} rmt_obj_t;

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

    // 创建编码器
    rmt_encoder_handle_t copy_encoder;
    rmt_copy_encoder_config_t copy_encoder_config = {};
    err = rmt_new_copy_encoder(&copy_encoder_config, &copy_encoder);
    if (err != ESP_OK)
    {
        mp_raise_msg_varg(
            &mp_type_Exception, MP_ERROR_TEXT("creaet_copy_encoder_error: %d"), err);
    }

    // 申请内存
    size_t buffer_size = sizeof(rmt_symbol_word_t) * data_len_t;
    void *mem_lr = heap_caps_malloc(buffer_size, MALLOC_CAP_DMA);
    if (!mem_lr)
    {
        mp_raise_msg_varg(
            &mp_type_Exception,
            MP_ERROR_TEXT("malloc_mem_error: %d"), err);
    }
    mp_obj_t ret_bytearray = mp_obj_new_bytearray_by_ref(buffer_size, mem_lr);

    // 数据放入堆中返回
    rmt_obj_t *rmt = malloc(sizeof(rmt_obj_t));
    // 千万别让mpy管理内存，它似乎会移动整理内存
    // rmt_obj_t *rmt = m_new_obj(rmt_obj_t);
    if (!rmt)
    {
        mp_raise_msg(&mp_type_Exception, MP_ERROR_TEXT("malloc_ret_p_error"));
    }
    rmt->tx_chan = tx_chan;
    rmt->copy_encoder = copy_encoder;

    // 发送配置
    rmt->tx_config = (rmt_transmit_config_t){
        .loop_count = 0,
        .flags.eot_level = 0,         // 结束保持低电平
        .flags.queue_nonblocking = 1, // 队列满时返回错误
    };

    return mp_obj_new_int_from_uint((mp_uint_t)rmt);
}

// 发送数据
static mp_obj_t rmt_loop(
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
