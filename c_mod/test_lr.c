#include "py/runtime.h"
#include "py/objarray.h"
#include "esp_heap_caps.h" // 必须引入 ESP-IDF 的堆内存头文件

// ==================== 1. 核心分配逻辑 ====================
// type = 0 表示 SRAM, type = 1 表示 PSRAM
mp_obj_t make_bytearray_in_region(size_t size, int type)
{
    void *ptr = NULL;

    if (type == 1)
    {
        // MALLOC_CAP_SPIRAM 确保内存一定来自外部 PSRAM
        ptr = heap_caps_malloc(size, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    }
    else
    {
        // MALLOC_CAP_INTERNAL 确保内存一定来自内部 SRAM
        ptr = heap_caps_malloc(size, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
    }

    // 健壮性检查
    if (ptr == NULL)
    {
        mp_raise_msg(&mp_type_MemoryError, MP_ERROR_TEXT("ESP32-S3 Memory allocation failed!"));
    }

    // 将 C 的原生指针包装为 MicroPython 的 bytearray 对象
    mp_obj_t bytearray_obj = mp_obj_new_bytearray(size, ptr);

    return bytearray_obj;
}

// ==================== 2. Python 映射函数 ====================

// 申请 RAM: mymodule.alloc_ram(size)
static mp_obj_t mymodule_alloc_ram(mp_obj_t size_obj)
{
    size_t size = mp_obj_get_int(size_obj);
    return make_bytearray_in_region(size, 0); // 0 = SRAM
}
MP_DEFINE_CONST_FUN_OBJ_1(mymodule_alloc_ram_obj, mymodule_alloc_ram);

// 申请 PSRAM: mymodule.alloc_psram(size)
static mp_obj_t mymodule_alloc_psram(mp_obj_t size_obj)
{
    size_t size = mp_obj_get_int(size_obj);
    return make_bytearray_in_region(size, 1); // 1 = PSRAM
}
MP_DEFINE_CONST_FUN_OBJ_1(mymodule_alloc_psram_obj, mymodule_alloc_psram);

// 【补全关键释放函数】手动回收系统堆内存: mymodule.free_bytearray(buf)
static mp_obj_t mymodule_free_bytearray(mp_obj_t buf_obj)
{
    // 确保传入的是 bytearray 类型
    if (mp_obj_is_type(buf_obj, &mp_type_bytearray))
    {
        mp_obj_array_t *array = MP_OBJ_TO_PTR(buf_obj);
        // 如果底层指针不为空，释放它
        if (array->items != NULL)
        {
            heap_caps_free(array->items);
            array->items = NULL; // 避免野指针
            array->len = 0;
        }
    }
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_1(mymodule_free_bytearray_obj, mymodule_free_bytearray);

// ==================== 3. 模块全局字典 ====================
static const mp_rom_map_elem_t mymodule_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_mymodule)},
    {MP_ROM_QSTR(MP_QSTR_alloc_ram), MP_ROM_PTR(&mymodule_alloc_ram_obj)},
    {MP_ROM_QSTR(MP_QSTR_alloc_psram), MP_ROM_PTR(&mymodule_alloc_psram_obj)},
    {MP_ROM_QSTR(MP_QSTR_free_bytearray), MP_ROM_PTR(&mymodule_free_bytearray_obj)}, // 现在顺序正确，可以找到声明了
};
static MP_DEFINE_CONST_DICT(mymodule_globals, mymodule_globals_table);

// ==================== 4. 模块对象本身与注册 ====================
const mp_obj_module_t mymodule_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mymodule_globals,
};

MP_REGISTER_MODULE(MP_QSTR_mymodule, mymodule_user_cmodule);