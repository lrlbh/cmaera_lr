#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "py/runtime.h"
#include "py/obj.h"

// 查看支持的校准方式
static mp_obj_t get_adc_cali()
{
    adc_cali_scheme_ver_t scheme_mask;
    esp_err_t err = adc_cali_check_scheme(&scheme_mask);

    if (err != ESP_OK)
    {
        mp_raise_msg_varg(&mp_type_Exception, MP_ERROR_TEXT("query_adc_cali_err: %d"), err);
    }

    return mp_obj_new_int(scheme_mask);
}

// 校准对象
typedef struct _adc_cali_obj_t
{
    adc_cali_handle_t handle;
    adc_cali_scheme_ver_t scheme_mask;
} adc_cali_obj_t;

// 创建校准对象
static mp_obj_t new_adc_cali(size_t n_args, const mp_obj_t *args)
{

    // 获取py参数
    int unit = mp_obj_get_int(args[0]);     // 单元ID
    int atten = mp_obj_get_int(args[1]);    // 衰减
    int bitwidth = mp_obj_get_int(args[2]); // 位宽
    int chan = mp_obj_get_int(args[3]);     // 通道在S3上刚好是 gpio编号 -1

    // 创建返回对象
    adc_cali_obj_t *adc_cali = malloc(sizeof(adc_cali_obj_t));
    if (!adc_cali)
    {
        mp_raise_msg(&mp_type_Exception, MP_ERROR_TEXT("new_adc_cali_error: malloc"));
    }
    adc_cali->handle = NULL;

    // 曲线拟合
#if ADC_CALI_SCHEME_CURVE_FITTING_SUPPORTED

    adc_cali_curve_fitting_config_t cfg = {
        .chan = chan,
        .unit_id = unit,
        .atten = atten,
        .bitwidth = bitwidth,
    };
    esp_err_t err = adc_cali_create_scheme_curve_fitting(&cfg, &adc_cali->handle);
    if (err != ESP_OK)
    {
        free(adc_cali);
        mp_raise_msg_varg(&mp_type_Exception, MP_ERROR_TEXT("new_adc_cali_CURVE_error: %d"), err);
    }

    adc_cali->scheme_mask = ADC_CALI_SCHEME_VER_CURVE_FITTING;
    return mp_obj_new_int_from_uint((mp_uint_t)adc_cali);

    // 线性拟合
#elif ADC_CALI_SCHEME_LINE_FITTING_SUPPORTED
    adc_cali_line_fitting_config_t cfg = {
        .unit_id = unit,
        .atten = atten,
        .bitwidth = bitwidth,
    };
    esp_err_t err = adc_cali_create_scheme_line_fitting(&cfg, &adc_cali->handle);
    if (err != ESP_OK)
    {
        free(adc_cali);
        mp_raise_msg_varg(&mp_type_Exception, MP_ERROR_TEXT("new_adc_cali_LINE_error: %d"), err);
    }

    adc_cali->scheme_mask = ADC_CALI_SCHEME_VER_LINE_FITTING;
    return mp_obj_new_int_from_uint((mp_uint_t)adc_cali);
#endif

    // 不支持校准
    free(adc_cali);
    mp_raise_msg(&mp_type_Exception, MP_ERROR_TEXT("new_adc_cali_error: NO_cali"));
}

// 获取校准数据
static mp_obj_t adc_cali_data(mp_obj_t adc_cali_in, mp_obj_t in_data_in)
{

    // 获取参数
    adc_cali_obj_t *adc_cal = (adc_cali_obj_t *)mp_obj_get_uint(adc_cali_in);
    int in_data = mp_obj_get_int(in_data_in);

    // 获取校准值
    int out_data = 0;
    esp_err_t err = adc_cali_raw_to_voltage(adc_cal->handle, in_data, &out_data);
    if (err != ESP_OK)
    {
        mp_raise_msg_varg(&mp_type_Exception, MP_ERROR_TEXT("get_adc_cali_error: %d"), err);
    }

    return mp_obj_new_int(out_data);
}

// 释放校准对象
static mp_obj_t adc_cali_close(mp_obj_t adc_cali_in)
{
    adc_cali_obj_t *adc_cal = (adc_cali_obj_t *)mp_obj_get_uint(adc_cali_in);
    esp_err_t err = ESP_ERR_NOT_SUPPORTED;

    if (adc_cal && adc_cal->handle)
    {
#if ADC_CALI_SCHEME_CURVE_FITTING_SUPPORTED

        err = adc_cali_delete_scheme_curve_fitting(adc_cal->handle);

#elif ADC_CALI_SCHEME_LINE_FITTING_SUPPORTED

        err = adc_cali_delete_scheme_line_fitting(adc_cal->handle);
#endif
        if (err != ESP_OK)
        {
            mp_raise_msg_varg(&mp_type_Exception, MP_ERROR_TEXT("adc_cali_close_error: %d"), err);
        }

        adc_cal->handle = NULL;
        free(adc_cal);
    }

    return mp_const_none;
}

// 在下方提供注册到mpy的代码,模块名: adc_cali_lr, static用小写,static用小写
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须

// 定义 Python 函数对象
// get_adc_cali() -> 0 arguments
static MP_DEFINE_CONST_FUN_OBJ_0(get_adc_cali_obj, get_adc_cali);

// new_cali(unit, atten, bitwidth, chan) -> 4 arguments
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(new_adc_cali_obj, 4, 4, new_adc_cali);

// adc_cali_data(handle, raw_val) -> 2 arguments
static MP_DEFINE_CONST_FUN_OBJ_2(adc_cali_data_obj, adc_cali_data);

// adc_cali_close(handle) -> 1 argument
static MP_DEFINE_CONST_FUN_OBJ_1(adc_cali_close_obj, adc_cali_close);

// 映射表：建立 Python 名称与 C 对象的关系
static const mp_rom_map_elem_t adc_cali_lr_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__),      MP_ROM_QSTR(MP_QSTR_adc_cali_lr) },
    { MP_ROM_QSTR(MP_QSTR_get_adc_cali),  MP_ROM_PTR(&get_adc_cali_obj) },
    { MP_ROM_QSTR(MP_QSTR_new_adc_cali),      MP_ROM_PTR(&new_adc_cali_obj) },
    { MP_ROM_QSTR(MP_QSTR_adc_cali_data),  MP_ROM_PTR(&adc_cali_data_obj) },
    { MP_ROM_QSTR(MP_QSTR_adc_cali_close), MP_ROM_PTR(&adc_cali_close_obj) },
};

// 定义模块字典
static MP_DEFINE_CONST_DICT(adc_cali_lr_globals, adc_cali_lr_globals_table);

// 定义模块对象
const mp_obj_module_t adc_cali_lr_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&adc_cali_lr_globals,
};

// 注册模块到 MicroPython 系统
MP_REGISTER_MODULE(MP_QSTR_adc_cali_lr, adc_cali_lr_user_cmodule);