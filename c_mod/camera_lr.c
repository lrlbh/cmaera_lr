#include "py/obj.h"
#include "py/runtime.h"
#include "py/mperrno.h" // ← 添加这个头文件，解决 MP_EIO 未定义
#include "esp_camera.h"
#include "esp_err.h"
#include <string.h> // ← 添加 memset 需要的头文件
#include "py/objarray.h"
#include "esp_camera_af.h"

// 获取传感器指针
static sensor_t *get_s(void)
{
    sensor_t *s = esp_camera_sensor_get();
    if (!s)
    {
        mp_raise_msg(&mp_type_Exception, MP_ERROR_TEXT("carmera P == NULL"));
    }

    return s;
}

// 初始化摄像头
static mp_obj_t mp_camera_init(mp_obj_t config_obj)
{
    // ← 修改这里：使用 mp_obj_is_type 替代 mp_obj_is_dict
    if (!mp_obj_is_type(config_obj, &mp_type_dict))
    {
        mp_raise_TypeError(MP_ERROR_TEXT("config must be dict"));
    }

    mp_obj_dict_t *dict = MP_OBJ_TO_PTR(config_obj);
    camera_config_t config;

    // 默认清零
    memset(&config, 0, sizeof(config));

// 从 dict 取参数
#define GET_INT(key) \
    mp_obj_get_int(mp_obj_dict_get(dict, MP_OBJ_NEW_QSTR(MP_QSTR_##key)))

    config.pin_pwdn = GET_INT(pin_pwdn);
    config.pin_reset = GET_INT(pin_reset);
    config.pin_xclk = GET_INT(pin_xclk);

    config.pin_sccb_sda = GET_INT(pin_sccb_sda);
    config.pin_sccb_scl = GET_INT(pin_sccb_scl);

    config.pin_d7 = GET_INT(pin_d7);
    config.pin_d6 = GET_INT(pin_d6);
    config.pin_d5 = GET_INT(pin_d5);
    config.pin_d4 = GET_INT(pin_d4);
    config.pin_d3 = GET_INT(pin_d3);
    config.pin_d2 = GET_INT(pin_d2);
    config.pin_d1 = GET_INT(pin_d1);
    config.pin_d0 = GET_INT(pin_d0);

    config.pin_vsync = GET_INT(pin_vsync);
    config.pin_href = GET_INT(pin_href);
    config.pin_pclk = GET_INT(pin_pclk);

    config.xclk_freq_hz = GET_INT(xclk_freq_hz);

    config.ledc_timer = GET_INT(ledc_timer);
    config.ledc_channel = GET_INT(ledc_channel);

    config.pixel_format = GET_INT(pixel_format);
    config.frame_size = GET_INT(frame_size);

    config.jpeg_quality = GET_INT(jpeg_quality);
    config.fb_count = GET_INT(fb_count);

    config.fb_location = GET_INT(fb_location);
    config.grab_mode = GET_INT(grab_mode);

    config.sccb_i2c_port = GET_INT(sccb_i2c_port);

    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK)
    {
        mp_raise_OSError(err);
    }

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(camera_init_obj, mp_camera_init);

// 设置寄存器
static mp_obj_t mp_camera_set_reg(mp_obj_t reg_obj,
                                  mp_obj_t mask_obj,
                                  mp_obj_t value_obj)
{
    int reg = mp_obj_get_int(reg_obj);
    int mask = mp_obj_get_int(mask_obj);
    int value = mp_obj_get_int(value_obj);

    sensor_t *s = esp_camera_sensor_get();
    if (!s)
    {
        mp_raise_OSError(MP_ENODEV);
    }
    // s->status
    return mp_obj_new_int(s->set_reg(s, reg, mask, value));
}
static MP_DEFINE_CONST_FUN_OBJ_3(
    camera_set_reg_obj,
    mp_camera_set_reg);

// 获取寄存器值
static mp_obj_t mp_camera_get_reg(mp_obj_t reg_obj,
                                  mp_obj_t mask_obj)
{
    int reg = mp_obj_get_int(reg_obj);
    int mask = mp_obj_get_int(mask_obj);

    sensor_t *s = esp_camera_sensor_get();
    if (!s)
    {
        mp_raise_OSError(MP_ENODEV);
    }

    return mp_obj_new_int(s->get_reg(s, reg, mask));
}
static MP_DEFINE_CONST_FUN_OBJ_2(
    camera_get_reg_obj,
    mp_camera_get_reg);

// 设置自动对焦
static mp_obj_t mp_camera_af_run(void)
{

    sensor_t *s = esp_camera_sensor_get();
    if (!s)
    {
        mp_raise_OSError(MP_ENODEV);
    }

    esp_camera_af_config_t af_cfg = {
        .mode = ESP_CAMERA_AF_MODE_AUTO,
        .timeout_ms = 2000,
    };

    esp_err_t ret = esp_camera_af_init(s, &af_cfg);
    if (ret != ESP_OK)
    {
        mp_raise_msg_varg(&mp_type_OSError, MP_ERROR_TEXT("Camera AF init failed: %d"), ret);
    }

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(mp_camera_af_run_obj,
                                 mp_camera_af_run);

// 获取图像数据
static mp_obj_t mp_camera_get_img_data(void)
{
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb)
    {
        mp_raise_OSError(MP_EIO); // ← 现在这个可以正常使用了
    }

    // 拷贝数据到 micropython 管理内存
    mp_obj_t bytes_obj = mp_obj_new_bytes(fb->buf, fb->len);

    // 归还 frame buffer
    esp_camera_fb_return(fb);

    return bytes_obj;
}
static MP_DEFINE_CONST_FUN_OBJ_0(camera_get_img_data_obj, mp_camera_get_img_data);

// 获取图像指针
static mp_obj_t mp_camera_get_img_p(void)
{
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb)
    {
        mp_raise_OSError(MP_EIO);
    }

    mp_obj_t mv = mp_obj_new_memoryview('B', fb->len, fb->buf);
    mp_obj_t fb_ptr = mp_obj_new_int_from_ull((uintptr_t)fb);

    mp_obj_t tuple[2] = {mv, fb_ptr};
    return mp_obj_new_tuple(2, tuple);
}
static MP_DEFINE_CONST_FUN_OBJ_0(camera_get_img_p_obj, mp_camera_get_img_p);

// 返回图像指针
static mp_obj_t mp_camera_free_img_p(mp_obj_t fb_ptr_obj)
{
    camera_fb_t *fb = (camera_fb_t *)(uintptr_t)
        mp_obj_get_int_truncated(fb_ptr_obj);

    esp_camera_fb_return(fb);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(camera_get_free_p_obj, mp_camera_free_img_p);

/*----------------------------------------------------------
 * camera.deinit()
 *----------------------------------------------------------*/
static mp_obj_t mp_camera_deinit(void)
{
    esp_camera_deinit();
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(camera_deinit_obj, mp_camera_deinit);

// 设置分辨率
static mp_obj_t set_img_size(mp_obj_t size)
{
    sensor_t *s = get_s();

    int size_lr = mp_obj_get_int(size);

    return mp_obj_new_int(s->set_framesize(s, size_lr));
}
static MP_DEFINE_CONST_FUN_OBJ_1(set_img_size_obj, set_img_size);

// 设置jpeg质量
static mp_obj_t set_jepg_quality(mp_obj_t quality)
{
    sensor_t *s = get_s();

    return mp_obj_new_int(s->set_quality(s, mp_obj_get_int(quality)));
}
static MP_DEFINE_CONST_FUN_OBJ_1(set_jepg_quality_obj, set_jepg_quality);

// 水平镜像
static mp_obj_t set_hmirror(mp_obj_t enable)
{
    sensor_t *s = get_s();

    return mp_obj_new_int(s->set_hmirror(s, mp_obj_get_int(enable)));
}
static MP_DEFINE_CONST_FUN_OBJ_1(set_hmirror_obj, set_hmirror);

// 垂直翻转
static mp_obj_t set_vflip(mp_obj_t enable)
{
    sensor_t *s = get_s();

    return mp_obj_new_int(s->set_vflip(s, mp_obj_get_int(enable)));
}
static MP_DEFINE_CONST_FUN_OBJ_1(set_vflip_obj, set_vflip);

// 设置时钟树
static mp_obj_t set_pll(size_t n_args, const mp_obj_t *args)
{
    sensor_t *s = get_s();

    if (n_args != 8)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("set_pll needs 8 args"));
    }

    int bypass = mp_obj_get_int(args[0]);
    int mul = mp_obj_get_int(args[1]);
    int sys = mp_obj_get_int(args[2]);
    int root = mp_obj_get_int(args[3]);
    int pre = mp_obj_get_int(args[4]);
    int seld5 = mp_obj_get_int(args[5]);
    int pclken = mp_obj_get_int(args[6]);
    int pclk = mp_obj_get_int(args[7]);

    int ret = s->set_pll(
        s,
        bypass,
        mul,
        sys,
        root,
        pre,
        seld5,
        pclken,
        pclk);

    return mp_obj_new_int(ret);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(set_pll_obj, 8, 8, set_pll);

// 设置输入时钟
static mp_obj_t set_xclk(mp_obj_t timer, mp_obj_t xclk)
{
    sensor_t *s = get_s();

    return mp_obj_new_int(
        s->set_xclk(s, mp_obj_get_int(timer), mp_obj_get_int(xclk)));
}
static MP_DEFINE_CONST_FUN_OBJ_2(set_xclk_obj, set_xclk);

// 获取摄像头型号
static mp_obj_t get_pid(void)
{
    sensor_t *s = get_s();

    return mp_obj_new_int(s->id.PID);
}
static MP_DEFINE_CONST_FUN_OBJ_0(get_pid_obj, get_pid);

/*----------------------------------------------------------
 * 模块定义
 *----------------------------------------------------------*/
static const mp_rom_map_elem_t camera_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_camera)},

    // 初始化/反初始化
    {MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&camera_init_obj)},
    {MP_ROM_QSTR(MP_QSTR_deinit), MP_ROM_PTR(&camera_deinit_obj)},

    // 寄存器操作
    {MP_ROM_QSTR(MP_QSTR_set_reg), MP_ROM_PTR(&camera_set_reg_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_reg), MP_ROM_PTR(&camera_get_reg_obj)},

    // 图像设置
    {MP_ROM_QSTR(MP_QSTR_set_img_size), MP_ROM_PTR(&set_img_size_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_jepg_quality), MP_ROM_PTR(&set_jepg_quality_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_hmirror), MP_ROM_PTR(&set_hmirror_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_vflip), MP_ROM_PTR(&set_vflip_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_pid), MP_ROM_PTR(&get_pid_obj)},

    // 时钟设置
    {MP_ROM_QSTR(MP_QSTR_set_pll), MP_ROM_PTR(&set_pll_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_xclk), MP_ROM_PTR(&set_xclk_obj)},

    // 自动对焦
    {MP_ROM_QSTR(MP_QSTR_af_run), MP_ROM_PTR(&mp_camera_af_run_obj)},

    // 图像获取（拷贝数据，安全）
    {MP_ROM_QSTR(MP_QSTR_get_img_data), MP_ROM_PTR(&camera_get_img_data_obj)},

    // 图像获取（零拷贝，需手动释放）
    {MP_ROM_QSTR(MP_QSTR_get_img_p), MP_ROM_PTR(&camera_get_img_p_obj)},
    {MP_ROM_QSTR(MP_QSTR_free_img_p), MP_ROM_PTR(&camera_get_free_p_obj)},
};

static MP_DEFINE_CONST_DICT(camera_module_globals, camera_module_globals_table);

const mp_obj_module_t camera_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&camera_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_cameralr, camera_user_cmodule);

// cd ~/mpy/esp-idf
// . ./export.sh