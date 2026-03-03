#include "py/obj.h"
#include "py/runtime.h"
#include "py/mperrno.h" // ← 添加这个头文件，解决 MP_EIO 未定义
#include "esp_netif.h"
#include "lwip/ip6_addr.h"
// 申请IPV6地址
static mp_obj_t mp_get_ipv6(void)
{

    esp_netif_t *wifi_netif =
        esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");

    if (wifi_netif == NULL)
    {
        mp_raise_msg(&mp_type_Exception, MP_ERROR_TEXT("wifi P == NULL"));
    }

    esp_err_t err = esp_netif_create_ip6_linklocal(wifi_netif);
    if (err != ESP_OK)
    {
        mp_raise_msg(&mp_type_Exception, MP_ERROR_TEXT("ipv6_addr_get_error"));
    }

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(mp_get_ipv6_obj, mp_get_ipv6);

// 返回IPV6地址
static mp_obj_t mp_get_ipv6_addr(void) {
    esp_netif_t *netif = esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
    if (!netif) {
        mp_raise_msg(&mp_type_OSError, MP_ERROR_TEXT("wifi P == NULL"));
    }

    esp_ip6_addr_t ip6_addrs[3];
    int num_addr = esp_netif_get_all_ip6(netif, ip6_addrs);

    if (num_addr <= 0) {
        // 没有 IPv6，返回空列表
        return mp_obj_new_list(0, NULL);
    }

    // 创建 Python 列表
    mp_obj_list_t *py_list = MP_OBJ_TO_PTR(mp_obj_new_list(0, NULL));

    for (int i = 0; i < num_addr; i++) {
        // 转成 Python 字符串
        char str[64]; // 足够存 IPv6 字符串
        snprintf(str, sizeof(str), IPV6STR, IPV62STR(ip6_addrs[i]));
        mp_obj_list_append(MP_OBJ_FROM_PTR(py_list), mp_obj_new_str(str, strlen(str)));
    }

    return MP_OBJ_FROM_PTR(py_list);
}
static MP_DEFINE_CONST_FUN_OBJ_0(mp_get_ipv6_addr_obj, mp_get_ipv6_addr);

/*----------------------------------------------------------
 * 模块定义
 *----------------------------------------------------------*/
static const mp_rom_map_elem_t wifilr_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_wifilr)},

    // 初始化/反初始化
    {MP_ROM_QSTR(MP_QSTR_get_ipv6), MP_ROM_PTR(&mp_get_ipv6_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_ipv6_addr), MP_ROM_PTR(&mp_get_ipv6_addr_obj)},

};

static MP_DEFINE_CONST_DICT(wifilr_module_globals, wifilr_module_globals_table);

const mp_obj_module_t wifilr_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&wifilr_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_wifilr, wifilr_user_cmodule);
