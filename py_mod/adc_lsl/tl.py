import adc_cali_lr


def get_支持的校准模式() -> str:
    线性拟合 = 0x01
    曲线拟合 = 0x02

    # 当时没注意看，IDF校准方式=0时，err != ESP_OK
    # 所以现在，不支持校准时会抛出error ESP_ERR_NOT_SUPPORTED
    t = adc_cali_lr.get_adc_cali()

    支持 = []
    不支持 = []

    if t & 线性拟合:
        支持.append("线性拟合")
    else:
        不支持.append("线性拟合")

    if t & 曲线拟合:
        支持.append("曲线拟合")
    else:
        不支持.append("曲线拟合")

    结果 = ""
    if 支持:
        结果 += f"支持{', '.join(支持)}"
    if 不支持:
        if 结果:
            结果 += "，"
        结果 += f"不支持{', '.join(不支持)}"

    return 结果


# lib_lsl.send(get_支持的校准模式())
