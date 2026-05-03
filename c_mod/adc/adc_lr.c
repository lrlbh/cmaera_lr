#include "py/runtime.h"
#include "py/obj.h"
#include "esp_adc/adc_continuous.h"

typedef struct _adc_obj_t
{
    adc_continuous_handle_t handle; // adc对象

} adc_obj_t;

// 完成一帧的回调
// static bool s_conv_done_cb(adc_continuous_handle_t handle,
//                            const adc_continuous_evt_data_t *edata,
//                            void *user_data)
// {
//     // edata->size  → 本次完成的数据大小（字节）
//     // edata->buf   → 指向 DMA 缓冲区（注意：不要直接在这里处理耗时操作）

//     // 返回 true  → 触发任务通知，唤醒等待的 Task
//     // 返回 false → 不通知 Task
//     return true;
// }

static mp_obj_t new_adc(size_t n_args, const mp_obj_t *args)
{

    esp_err_t err;

    // 获取python传入变量
    mp_obj_list_t *channel = MP_OBJ_TO_PTR(args[0]);   // adc通道
    int mem_buf_size = mp_obj_get_int(args[1]);        // 内部缓冲区大小 字节 帧的2倍以上
    int frame_buf_size = mp_obj_get_int(args[2]);      // 帧大小 字节 每个adc值4字节
    int flush_flag = mp_obj_get_int(args[3]);          //  缓冲区满了的行为
                                                       // 0: 缓冲区满时覆盖旧数据
                                                       // 1:缓冲区满时清空整个缓冲区（flush），丢弃所有旧数据，从头开始存新数据
    mp_obj_list_t *atten = MP_OBJ_TO_PTR(args[4]);     // 衰减 0=0DB 1=2_5DB 2=6_DB 3 =12_DB
    mp_obj_list_t *unit = MP_OBJ_TO_PTR(args[5]);      // 单元: S3有2个 0是ADC 1是ADC2和 wifi冲突
    mp_obj_list_t *bit_width = MP_OBJ_TO_PTR(args[6]); // 精度: 可以直接用9~13, 0是自动选择最大
    int sample_freq = mp_obj_get_int(args[7]);         // 采样频率 611Hz ~ 83333Hz
    int format = mp_obj_get_int(args[8]);              // 输出数据格式 0 or 1 S3只有 1
    int conv_mode = mp_obj_get_int(args[9]);           // 1 == 只使用ADC1
                                                       // 2 == 只使用ADC2
                                                       // 3 == 同时使用ADC1和ADC2
                                                       // 7 == 交替使用ADC和ADC2

    // 创建返回值
    adc_obj_t *adc = malloc(sizeof(adc_obj_t));
    if (!adc)
    {
        mp_raise_msg(&mp_type_Exception, MP_ERROR_TEXT("new_adc_malloc_error"));
    }
    adc->handle = NULL;

    // 创建adc对象
    adc_continuous_handle_cfg_t handle_cfg = {
        .max_store_buf_size = mem_buf_size,
        .conv_frame_size = frame_buf_size,
        .flags.flush_pool = flush_flag,
    };
    err = adc_continuous_new_handle(&handle_cfg, &adc->handle);
    if (err != ESP_OK)
    {
        free(adc);
        mp_raise_msg_varg(
            &mp_type_Exception, MP_ERROR_TEXT("new_adc_handle_error: %d"), err);
    }

    // 每个通道的采样参数
    adc_digi_pattern_config_t adc_pattern[channel->len];
    for (size_t i = 0; i < channel->len; i++)
    {
        adc_pattern[i].channel = mp_obj_get_int(channel->items[i]);
        adc_pattern[i].atten = mp_obj_get_int(atten->items[i]);
        adc_pattern[i].unit = mp_obj_get_int(unit->items[i]);
        adc_pattern[i].bit_width = mp_obj_get_int(bit_width->items[i]);
    }
    adc_continuous_config_t cont_cfg = {
        .pattern_num = channel->len, // 使用的GPIO数量
        .adc_pattern = adc_pattern,  // 每个通道的采样参数
        .sample_freq_hz = sample_freq,
        .conv_mode = conv_mode,
        .format = format, // 输出数据格式,S3只有TYPE2,4字节
        /**
         * @brief ADC DMA 输出数据格式 (ESP32-S3)，每条采样结果占 4 字节 (32-bit)。
         *
         *  [31:18] reserved    保留位，忽略
         *  [17]    unit        ADC 单元：0 = ADC1，1 = ADC2
         *  [16:13] channel     通道号，若 < ADC_CHANNEL_MAX 则数据有效
         *  [12]    reserved    保留位，忽略
         *  [11:0]  data        ADC 原始采样值，12-bit 精度 (0~4095)
         */
    };
    err = adc_continuous_config(adc->handle, &cont_cfg);
    if (err != ESP_OK)
    {
        adc_continuous_deinit(adc->handle);
        free(adc);
        mp_raise_msg_varg(
            &mp_type_Exception, MP_ERROR_TEXT("new_adc_config_set_error: %d"), err);
    }

    // 注册回调
    // static TaskHandle_t s_task_handle = NULL;
    // s_task_handle = xTaskGetCurrentTaskHandle();

    // adc_continuous_evt_cbs_t cbs = {
    //     .on_conv_done = s_conv_done_cb, // 完成一帧的回调
    //     .on_pool_ovf = NULL,            // 缓冲区溢出回调
    // };
    // ESP_ERROR_CHECK(adc_continuous_register_event_callbacks(handle, &cbs, s_task_handle));

    // 开始采样
    // err = adc_continuous_start(adc->handle);
    // if (err != ESP_OK)
    // {
    //     adc_continuous_deinit(adc->handle);
    //     free(adc);
    //     mp_raise_msg_varg(
    //         &mp_type_Exception, MP_ERROR_TEXT("new_adc_start_error: %d"), err);
    // }

    return mp_obj_new_int_from_uint((mp_uint_t)adc);
}

static mp_obj_t adc_read(mp_obj_t adc_in, mp_obj_t data_p_in)
{

    // 获取py传入数据
    adc_obj_t *adc = (adc_obj_t *)mp_obj_get_uint(adc_in);
    if (!adc || !adc->handle)
    {
        mp_raise_msg(&mp_type_Exception, MP_ERROR_TEXT("adc_read_error: adc == NULL"));
    }
    mp_buffer_info_t data;
    mp_get_buffer_raise(data_p_in, &data, MP_BUFFER_RW);

    // 获取采样值
    uint32_t read_len = 0;
    esp_err_t err = adc_continuous_read(
        adc->handle,
        data.buf,  // 接收数据
        data.len,  // 接收数据长度
        &read_len, // 实际接收长度
        0          // 等待时间,非阻塞
    );

    // 无数据，返回长度 0，不报错
    if (err == ESP_ERR_TIMEOUT)
    {
        return mp_obj_new_int(read_len);
    }

    if (err != ESP_OK)
    {
        mp_raise_msg_varg(&mp_type_Exception, MP_ERROR_TEXT("adc_read_error: %d"), err);
    }

    return mp_obj_new_int(read_len);
}

// 释放资源
static mp_obj_t adc_close(mp_obj_t adc_in)
{

    adc_obj_t *adc = (adc_obj_t *)mp_obj_get_uint(adc_in);

    if (adc && adc->handle)
    {

        esp_err_t err = adc_continuous_deinit(adc->handle);
        if (err != ESP_OK)
        {
            mp_raise_msg_varg(&mp_type_Exception, MP_ERROR_TEXT("adc_close_error: %d"), err);
        }

        adc->handle = NULL;
        free(adc);
    }

    return mp_const_none;
}

// 关闭转换
static mp_obj_t adc_stop(mp_obj_t adc_in)
{

    adc_obj_t *adc = (adc_obj_t *)mp_obj_get_uint(adc_in);
    if (adc && adc->handle)
    {
        esp_err_t err = adc_continuous_stop(adc->handle);
        if (err != ESP_OK)
        {
            mp_raise_msg_varg(&mp_type_Exception, MP_ERROR_TEXT("adc_stop_error: %d"), err);
        }
    }

    return mp_const_none;
}

// 开启转换
static mp_obj_t adc_start(mp_obj_t adc_in)
{

    adc_obj_t *adc = (adc_obj_t *)mp_obj_get_uint(adc_in);
    if (adc && adc->handle)
    {
        esp_err_t err = adc_continuous_start(adc->handle);
        if (err != ESP_OK)
        {
            mp_raise_msg_varg(&mp_type_Exception, MP_ERROR_TEXT("adc_start_error: %d"), err);
        }
    }

    return mp_const_none;
}

// 在下方提供注册到mpy的代码,模块名: adc_lr,static用小写
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须

// ========== MicroPython 模块注册 ==========

// 定义参数数量
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(new_adc_obj, 10, 10, new_adc);
static MP_DEFINE_CONST_FUN_OBJ_2(adc_read_obj, adc_read);
static MP_DEFINE_CONST_FUN_OBJ_1(adc_close_obj, adc_close);
static MP_DEFINE_CONST_FUN_OBJ_1(adc_stop_obj, adc_stop);
static MP_DEFINE_CONST_FUN_OBJ_1(adc_start_obj, adc_start);

// 定义模块全局表 —— C函数名 == PY函数名
static const mp_rom_map_elem_t adc_lr_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR_new_adc), MP_ROM_PTR(&new_adc_obj)},
    {MP_ROM_QSTR(MP_QSTR_adc_read), MP_ROM_PTR(&adc_read_obj)},
    {MP_ROM_QSTR(MP_QSTR_adc_close), MP_ROM_PTR(&adc_close_obj)},
    {MP_ROM_QSTR(MP_QSTR_adc_stop), MP_ROM_PTR(&adc_stop_obj)},
    {MP_ROM_QSTR(MP_QSTR_adc_start), MP_ROM_PTR(&adc_start_obj)},
};
static MP_DEFINE_CONST_DICT(adc_lr_module_globals, adc_lr_module_globals_table);

// 定义模块对象
const mp_obj_module_t adc_lr_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&adc_lr_module_globals,
};

// 注册模块
MP_REGISTER_MODULE(MP_QSTR_adc_lr, adc_lr_user_cmodule);
