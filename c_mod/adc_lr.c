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

// 在下方提供注册到mpy的代码，C函数名 == PY函数名 模块名: adc_lr
// 在下方提供注册到mpy的代码，C函数名 == PY函数名 模块名: adc_lr
// 在下方提供注册到mpy的代码，C函数名 == PY函数名 模块名: adc_lr
// 1. 定义 MicroPython 函数对象
// MP_DEFINE_CONST_FUN_OBJ_0 表示该函数接受 0 个参数
static MP_DEFINE_CONST_FUN_OBJ_0(get_adc_cali_obj, get_adc_cali);

// 2. 定义模块的全局字典
static const mp_rom_map_elem_t adc_lr_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_adc_lr)},
    {MP_ROM_QSTR(MP_QSTR_get_adc_cali), MP_ROM_PTR(&get_adc_cali_obj)},
};

// 创建字典结构
static MP_DEFINE_CONST_DICT(adc_lr_module_globals, adc_lr_module_globals_table);

// 3. 定义模块对象
const mp_obj_module_t adc_lr_user_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&adc_lr_module_globals,
};

// 4. 将模块注册到 MicroPython
// 注意：这通常需要你在 mpconfigport.h 中定义或者在编译脚本中包含
MP_REGISTER_MODULE(MP_QSTR_adc_lr, adc_lr_user_module);