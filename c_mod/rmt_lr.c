/*
    万万没想到IDF中关于RMT的发送不是连续的
    这里只能在重新实现一次RMT的c_mod了
*/

#include "driver/rmt_tx.h"
#include "py/runtime.h"
#include "py/obj.h"
#include "driver/rmt_encoder.h"
#include <string.h>

typedef struct _rmt_obj_t
{
    rmt_channel_handle_t tx_chan;
    rmt_encoder_handle_t encoder;
    rmt_transmit_config_t tx_config;
    int this_len;
    int tt;
    void *buf;
} rmt_obj_t;

// 获取int值
static mp_obj_t rmt_get_free(mp_obj_t rmt_in)
{
    rmt_obj_t *rmt = (rmt_obj_t *)mp_obj_get_uint(rmt_in);
    return mp_obj_new_int(rmt->this_len);
}

// 获取int值
static mp_obj_t rmt_get_tt(mp_obj_t rmt_in)
{
    rmt_obj_t *rmt = (rmt_obj_t *)mp_obj_get_uint(rmt_in);
    return mp_obj_new_int(rmt->tt);
}

// rmt_simple_encoder_config_t simple_encoder_config = {
//     .callback = test_enc, // 编码器回调

static size_t IRAM_ATTR test_enc(
    const void *data_in,         // 内外部共享内存地址
    size_t data_size,            // 内外部共享内存长度,单位字节
    size_t this_len,             // 当前发送到哪里了
    size_t data_out_len,         // 本次可以写入最大长度
    rmt_symbol_word_t *data_out, // 本次写入地址
    bool *done,                  // 传输完成标记,千万千万不能设置为true
                                 // 否则即使发送参数是死循环,也不会进入回调了
    void *arg_in)                // 自定义数据
{

    rmt_obj_t *arg = (rmt_obj_t *)arg_in;
    arg->this_len++;

    // 填满所有可用空间
    for (int i = 0; i < data_out_len; i++)
    {
        data_out[i].duration0 = arg->this_len;
        data_out[i].level0 = 1;
        data_out[i].duration1 = arg->this_len;
        data_out[i].level1 = 0;
    }

    if (this_len * 4 >= data_size)
    {
        *done = true;
    }

    // 发送参数里面死循环是假的，不会生效，所以返回true,回调将再也不会被执行
    // 如果在编码器完数据后还试图返回false，那么IDF将奔溃重启
    // 所以在编码器中也无法实现RMT连续模式
    *done = false;
    return 100;
}

// 创建通道
static mp_obj_t new_rmt(size_t n_args, const mp_obj_t *args)
{

    int gpio = mp_obj_get_int(args[0]);
    int data_len = mp_obj_get_int(args[1]);
    int gpio_cache = mp_obj_get_int(args[2]);
    int dma = mp_obj_get_int(args[3]);
    int intr_priority = mp_obj_get_int(args[4]);
    int is_od = mp_obj_get_int(args[5]);

    // 需要返回的对象
    rmt_obj_t *rmt = malloc(sizeof(rmt_obj_t));
    // 别让mpy管理内存，它似乎会整理移动内存 rmt_obj_t *rmt = m_new_obj(rmt_obj_t);
    if (!rmt)
    {
        mp_raise_msg(&mp_type_Exception, MP_ERROR_TEXT("malloc_ret_p_error"));
    }
    rmt->this_len = 0;
    rmt->tt = 0;

    // 通道配置
    rmt_tx_channel_config_t tx_chan_config = {
        .clk_src = RMT_CLK_SRC_DEFAULT,  // 选择时钟源：80MHz APB
        .gpio_num = gpio,                // 选择输出引脚
        .mem_block_symbols = gpio_cache, // 通道中保存多少个 rmt_symbol_word_t
        .resolution_hz = 80000000,       // 时钟源频率   1 tick = 12.5ns
        .trans_queue_depth = 2,          // 传输队列深度，实际无意义，因为切换队列时，输出会被停止
        .flags.with_dma = dma,           // 开启 DMA 模式
        .intr_priority = intr_priority,  // 中断优先级，传0驱动自动分配为低优先级
        .flags.io_od_mode = is_od};      // 0推挽，1开漏

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
    rmt_simple_encoder_config_t simple_encoder_config = {
        .callback = test_enc, // 编码器回调
        .arg = rmt,           // 传入数据
        .min_chunk_size = 32, /*    不知道这傻逼参数要干什么
                                    看样子是说有最少多少空位才触发回调
                                    然而，非dma情况下每个通道只有48个空间，它默认64？？？
                                    如果没有通道合并，默认就是BUG，回调不会被触????
                                    翻译了1个小时也不知道想表达什么
                                    傻逼东西    */
    };
    err = rmt_new_simple_encoder(&simple_encoder_config, &rmt->encoder);
    if (err != ESP_OK)
    {
        mp_raise_msg_varg(
            &mp_type_Exception, MP_ERROR_TEXT("create_simple_encoder_error: %d"), err);
    }

    // 申请申请缓冲区
    void *mem_lr = heap_caps_malloc(data_len, MALLOC_CAP_DMA);
    // memset(mem_lr, 0x00, data_len);
    if (!mem_lr)
    {
        mp_raise_msg_varg(
            &mp_type_Exception,
            MP_ERROR_TEXT("malloc_mem_error: %d"), err);
    }

    // 发送配置
    rmt->tx_config = (rmt_transmit_config_t){
        .loop_count = -1,             // 死循环发送，必须死循环发送，否则不是连续模式
        .flags.eot_level = 0,         // 结束保持低电平
        .flags.queue_nonblocking = 1, // 队列满时返回错误
    };

    // 返回，rmt对象和共享内存
    mp_obj_t ret_bytearray = mp_obj_new_bytearray_by_ref(data_len, mem_lr);
    mp_obj_t tuple[2] = {mp_obj_new_int_from_uint((uintptr_t)rmt), ret_bytearray};
    return mp_obj_new_tuple(2, tuple);
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

// 在下方提供注册到mpy的代码， 模块名: rmt_lr
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须

// new_rmt 接收变长参数 (args[0] 到 args[4])
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(new_rmt_obj, 6, 6, new_rmt);

// rmt_loop 接收 3 个参数
MP_DEFINE_CONST_FUN_OBJ_3(rmt_loop_obj, rmt_loop);

// rmt_get_symbol_size 接收 0 个参数
MP_DEFINE_CONST_FUN_OBJ_0(rmt_get_symbol_size_obj, rmt_get_symbol_size);

// 以下均接收 1 个参数 (rmt_in)
MP_DEFINE_CONST_FUN_OBJ_1(rmt_stop_channel_obj, rmt_stop_channel);
MP_DEFINE_CONST_FUN_OBJ_1(rmt_delete_encoder_obj, rmt_delete_encoder);
MP_DEFINE_CONST_FUN_OBJ_1(rmt_delete_channel_obj, rmt_delete_channel);
MP_DEFINE_CONST_FUN_OBJ_1(rmt_get_free_obj, rmt_get_free);
MP_DEFINE_CONST_FUN_OBJ_1(rmt_get_tt_obj, rmt_get_tt);

static const mp_rom_map_elem_t rmt_lr_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_rmt_lr)},

    // { Python函数名, C对象引用 }
    {MP_ROM_QSTR(MP_QSTR_rmt_get_free), MP_ROM_PTR(&rmt_get_free_obj)},
    {MP_ROM_QSTR(MP_QSTR_rmt_get_tt), MP_ROM_PTR(&rmt_get_tt_obj)},
    {MP_ROM_QSTR(MP_QSTR_new_rmt), MP_ROM_PTR(&new_rmt_obj)},
    {MP_ROM_QSTR(MP_QSTR_rmt_loop), MP_ROM_PTR(&rmt_loop_obj)},
    {MP_ROM_QSTR(MP_QSTR_rmt_get_symbol_size), MP_ROM_PTR(&rmt_get_symbol_size_obj)},
    {MP_ROM_QSTR(MP_QSTR_rmt_stop_channel), MP_ROM_PTR(&rmt_stop_channel_obj)},
    {MP_ROM_QSTR(MP_QSTR_rmt_delete_encoder), MP_ROM_PTR(&rmt_delete_encoder_obj)},
    {MP_ROM_QSTR(MP_QSTR_rmt_delete_channel), MP_ROM_PTR(&rmt_delete_channel_obj)},
};

// 定义字典结构
static MP_DEFINE_CONST_DICT(rmt_lr_globals, rmt_lr_globals_table);

const mp_obj_module_t rmt_lr_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&rmt_lr_globals,
};

// 注册模块到 MicroPython 编译系统
// 这样在 Python 中就可以 import rmt_lr 了
MP_REGISTER_MODULE(MP_QSTR_rmt_lr, rmt_lr_user_cmodule);

// ELF file SHA256: e2cd8cf53

// Rebooting...
// ���ESP-ROM:esp32s3-20210327
// Build:Mar 27 2021
// rst:0xc (RTC_SW_CPU_RST),boot:0x28 (SPI_FAST_FLASH_BOOT)
// Saved PC:0x4201adaa
// SPIWP:0xee
// mode:DIO, clock div:1
// load:0x3fce2820,len:0xeac
// load:0x403c8700,len:0xc28
// load:0x403cb700,len:0x2ff8
// entry 0x403c88ac
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encoding artifacts can't exceed hw memory block for loop transmission
// E rmt: encod
// A fatal error occurred. The crash dump printed below may be used to help
// determine what caused it. If you are not already running the most recent
// version of MicroPython, consider upgrading. New versions often fix bugs.

// To learn more about how to debug and/or report this crash visit the wiki
// page at: https://github.com/micropython/micropython/wiki/ESP32-debugging

// MPY version : v1.27.0-dirty on 2026-04-20
// IDF version : v5.5.1
// Machine     : Generic ESP32S3 module with Octal-SPIRAM with ESP32S3

// Guru Meditation Error: Core  1 panic'ed (Interrupt wdt timeout on CPU1).

// Core  1 register dump:
// PC      : 0x4004883e  PS      : 0x00060734  A0      : 0x80048c6c  A1      : 0x3fca79c0
// A2      : 0x0000e080  A3      : 0x00000069  A4      : 0x00000002  A5      : 0x00000001
// A6      : 0x3fccc614  A7      : 0x4203e42c  A8      : 0x60000000  A9      : 0x00000380
// A10     : 0x00000069  A11     : 0x6000001c  A12     : 0x3fcef130  A13     : 0x00000001
// A14     : 0x00006720  A15     : 0x3c1d0b24  SAR     : 0x0000001d  EXCCAUSE: 0x00000006
// EXCVADDR: 0x00000000  LBEG    : 0x00000000  LEND    : 0x00000000  LCOUNT  : 0x00000000
// Core  1 was running in ISR context:
// EPC1    : 0x4038c63f  EPC2    : 0x00000000  EPC3    : 0x00000000  EPC4    : 0x4004883e

// Backtrace: 0x4004883b:0x3fca79c0 0x40048c69:0x3fca79e0 0x40043d03:0x3fca7a00 0x40043cd5:0x3fca7a20 0x40044183:0x3fca7a40 0x40044281:0x3fca7ac0 0x4203def5:0x3fca7b10 0x4203e45a:0x3fca7b40 0x4038319e:0x3fca7b60 0x4037ec7e:0x3fca7b90 0x403831bb:0x3fcb8140 0x42156d5e:0x3fcb8160 0x42156db4:0x3fcb8180 0x40388d3c:0x3fcb81a0

// Core  0 register dump:
// PC      : 0x40382e66  PS      : 0x00060434  A0      : 0x82156d61  A1      : 0x3fcb79d0
// A2      : 0x00060423  A3      : 0x00000000  A4      : 0x00060420  A5      : 0x3fcb4a60
// A6      : 0x3fcb64c0  A7      : 0x3fcb64a8  A8      : 0x8037efd6  A9      : 0x3fcb79b0
// A10     : 0x3fcb64c0  A11     : 0x00000001  A12     : 0x00000000  A13     : 0x00000000
// A14     : 0x01ffffff  A15     : 0x00000008  SAR     : 0x0000001d  EXCCAUSE: 0x00000006
// EXCVADDR: 0x00000000  LBEG    : 0x00000000  LEND    : 0x00000000  LCOUNT  : 0x00000000

// Backtrace: 0x40382e63:0x3fcb79d0 0x42156d5e:0x3fcb79f0 0x42156db4:0x3fcb7a10 0x40388d3c:0x3fcb7a30

// ELF file SHA256: e2cd8cf53

// Rebooting...
// ���ESP-ROM:esp32s3-20210327
// Build:Mar 27 2021
// rst:0xc (RTC_SW_CPU_RST),boot:0x28 (SPI_FAST_FLASH_BOOT)
// Saved PC:0x4201adaa
// SPIWP:0xee
// mode:DIO, clock div:1
// load:0x3fce2820,len:0xeac
// load:0x403c8700,len:0xc28
// load:0x403cb700,len:0x2ff8
// entry 0x403c88ac