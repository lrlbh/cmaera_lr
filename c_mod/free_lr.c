#include "driver/rmt_tx.h"
#include "py/runtime.h"
#include "py/obj.h"

// 释放malloc申请的
static mp_obj_t free_lr(mp_obj_t p_in)
{
    void *p = (void *)mp_obj_get_uint(p_in);

    if (p != NULL)
    {
        // 释放由 malloc 申请的内存
        free(p);
    }

    return mp_const_none;
}

// 释放heap_caps_malloc申请，保存在bytearray中的内存
static mp_obj_t heap_caps_free_bytearray_lr(mp_obj_t data_in)
{
    mp_buffer_info_t byteay;
    mp_get_buffer_raise(data_in, &byteay, MP_BUFFER_READ);

    if (byteay.buf != NULL)
    {
        heap_caps_free(byteay.buf); // 释放底层内存
    }

    return mp_const_none;
}

// 为每个 C 函数定义一个 MicroPython 函数对象
static MP_DEFINE_CONST_FUN_OBJ_1(free_lr_obj, free_lr);
static MP_DEFINE_CONST_FUN_OBJ_1(heap_caps_free_bytearray_lr_obj, heap_caps_free_bytearray_lr);

// 建立模块的全局字典映射
static const mp_rom_map_elem_t free_lr_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_free_lr)},
    {MP_ROM_QSTR(MP_QSTR_free_lr), MP_ROM_PTR(&free_lr_obj)},
    {MP_ROM_QSTR(MP_QSTR_heap_caps_free_bytearray_lr), MP_ROM_PTR(&heap_caps_free_bytearray_lr_obj)},
};
static MP_DEFINE_CONST_DICT(free_lr_module_globals, free_lr_module_globals_table);

// 定义模块对象
const mp_obj_module_t free_lr_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&free_lr_module_globals,
};

// 注册模块到系统。模块名：free_lr
MP_REGISTER_MODULE(MP_QSTR_free_lr, free_lr_user_cmodule);