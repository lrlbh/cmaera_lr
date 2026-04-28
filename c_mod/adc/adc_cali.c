#include "esp_adc/adc_cali.h"
#include "py/runtime.h"
#include "py/obj.h"

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

// 在下方提供注册到mpy的代码,模块名: adc_cali_lr, static用小写,static用小写
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须
// 必须必须必须!!!C函数名 == PY函数名!!!必须必须必须

// 定义参数数量
static MP_DEFINE_CONST_FUN_OBJ_0(get_adc_cali_obj, get_adc_cali);

// 定义模块全局表 —— C函数名 == PY函数名
static const mp_rom_map_elem_t adc_cali_lr_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR_get_adc_cali), MP_ROM_PTR(&get_adc_cali_obj)},
};
static MP_DEFINE_CONST_DICT(adc_cali_lr_module_globals, adc_cali_lr_module_globals_table);

// 定义模块对象
const mp_obj_module_t adc_cali_lr_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&adc_cali_lr_module_globals,
};

// 注册模块
MP_REGISTER_MODULE(MP_QSTR_adc_cali_lr, adc_cali_lr_user_cmodule);
