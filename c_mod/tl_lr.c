#include "py/runtime.h"
#include <stdint.h>

// ws掩码运算,放入C中加速
static mp_obj_t ws_mask_decode(mp_obj_t data_obj, mp_obj_t mask_obj)
{
    mp_buffer_info_t data_buf;
    mp_buffer_info_t mask_buf;

    // 数据必须可写
    mp_get_buffer_raise(data_obj, &data_buf, MP_BUFFER_RW);

    // mask只读即可
    mp_get_buffer_raise(mask_obj, &mask_buf, MP_BUFFER_READ);

    // if (mask_buf.len != 4)
    // {
    //     mp_raise_ValueError(MP_ERROR_TEXT("mask length must be 4"));
    // }

    uint8_t *data = (uint8_t *)data_buf.buf;
    const uint8_t *mask = (const uint8_t *)mask_buf.buf;

    size_t len = data_buf.len;

    size_t i = 0;

    // 先处理4字节对齐部分
    for (; i + 4 <= len; i += 4)
    {
        data[i + 0] ^= mask[0];
        data[i + 1] ^= mask[1];
        data[i + 2] ^= mask[2];
        data[i + 3] ^= mask[3];
    }

    // 剩余不足4字节
    while (i < len)
    {
        data[i] ^= mask[i & 3];
        i++;
    }

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(ws_mask_decode_obj, ws_mask_decode);

// ws掩码运算,放入C中加速,对比上方函数似乎更快10%左右
static mp_obj_t ws_mask_decode_2(mp_obj_t data_obj, mp_obj_t mask_obj)
{
    mp_buffer_info_t data_buf;
    mp_buffer_info_t mask_buf;

    mp_get_buffer_raise(data_obj, &data_buf, MP_BUFFER_RW);
    mp_get_buffer_raise(mask_obj, &mask_buf, MP_BUFFER_READ);

    uint8_t *data = (uint8_t *)data_buf.buf;
    const uint8_t *mask = (const uint8_t *)mask_buf.buf;

    size_t len = data_buf.len;

    size_t offset = 0;

    // 处理直到4字节对齐
    while (len && ((uintptr_t)data & 3))
    {
        data[0] ^= mask[offset & 3];

        data++;
        offset++;
        len--;
    }

    // 根据当前mask偏移重新生成key
    uint32_t key =
        ((uint32_t)mask[(offset + 0) & 3]) |
        ((uint32_t)mask[(offset + 1) & 3] << 8) |
        ((uint32_t)mask[(offset + 2) & 3] << 16) |
        ((uint32_t)mask[(offset + 3) & 3] << 24);

    // 4字节处理
    uint32_t *p = (uint32_t *)data;

    while (len >= 4)
    {
        *p ^= key;

        p++;
        len -= 4;
    }

    data = (uint8_t *)p;

    // 剩余字节
    while (len)
    {
        data[0] ^= mask[offset & 3];

        data++;
        offset++;
        len--;
    }

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(ws_mask_decode_2_obj, ws_mask_decode_2);

// 定义模块
static const mp_rom_map_elem_t tl_lr_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__),
     MP_ROM_QSTR(MP_QSTR_tl_lr)},

    {MP_ROM_QSTR(MP_QSTR_ws_mask_decode),
     MP_ROM_PTR(&ws_mask_decode_obj)},

    {MP_ROM_QSTR(MP_QSTR_ws_mask_decode_2),
     MP_ROM_PTR(&ws_mask_decode_2_obj)},
};
static MP_DEFINE_CONST_DICT(tl_lr_globals, tl_lr_globals_table);

// 创建模块对象
const mp_obj_module_t tl_lr_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&tl_lr_globals,
};

// 注册模块
MP_REGISTER_MODULE(MP_QSTR_tl_lr, tl_lr_user_cmodule);