from machine import SPI
import lcd_lsl
import ul

ul.send(123)

ul.send(lcd_lsl.预设色24位)
ul.send("------------")
spi = SPI(1)

tft = lcd_lsl.LCD(spi, 20)
tft.new_txt("斯顿", 32, 3000)
tft.new_波形(0, 0, 0, 0, 0, [1], [1], [2], [tft.color.中灰], tft.color.中灰)
print(tft.color.橙)
print(tft.color)

ul.send("end")
