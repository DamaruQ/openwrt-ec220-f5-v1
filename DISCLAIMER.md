# Disclaimer / Предупреждение


Эта прошивка сделана **в первую очередь для моего собственного TP-Link EC220-F5 V1**, чтобы мой конкретный роутер нормально работал на OpenWrt. На моём экземпляре проверены TFTP-установка, LAN/WAN, 2.4/5 ГГц Wi-Fi, SPI 40 МГц и последующий `sysupgrade`.

При этом я **не гарантирую**, что прошивка будет работать на любом другом экземпляре EC220-F5, другой аппаратной ревизии, операторской версии или варианте комплектующих. Любая прошивка выполняется **полностью на ваш страх и риск**. Возможны потеря настроек, неработоспособность устройства и необходимость восстановления через TFTP или программатор.

Проект публикуется **как есть (AS IS), без каких-либо гарантий**. Я не беру на себя ответственность за повреждение роутера, потерю конфигурации, данных или любые другие последствия использования этих файлов.

Это не коммерческий продукт и не поддерживаемый форк OpenWrt. Я делал этот порт для себя и **не обещаю дальнейшую поддержку, исправление багов, новые версии, обновления или адаптацию под другие ревизии/модели**. Если что-то не работает на вашем устройстве, не следует рассчитывать, что я буду это дорабатывать.

Перед прошивкой обязательно сохраните штатный recovery и, по возможности, индивидуальные разделы устройства (`boot`, `config`, `rom`, `romfile`, `radio`).

---


This firmware was created **primarily for my own TP-Link EC220-F5 V1**, so that my particular router could run OpenWrt properly. On my unit, TFTP installation, LAN/WAN, 2.4/5 GHz Wi-Fi, 40 MHz SPI and a real follow-up `sysupgrade` were tested successfully.

I **do not guarantee** that it will work on every EC220-F5 unit, another hardware revision, ISP-specific variant, or different component/BOM variant. Flashing is **entirely at your own risk**. You may lose configuration, render the router unbootable, or need TFTP recovery or an external programmer.

This project is provided **AS IS, without warranty of any kind**. I accept no responsibility for damaged hardware, lost configuration/data, or any other consequences resulting from use of these files.

This is not a commercial product and not a supported OpenWrt fork. I built this port for myself and **do not promise future support, bug fixes, new releases, updates, or adaptation for other hardware revisions/models**. If it does not work on your unit, do not assume that I will investigate or maintain it.

Before flashing, keep a stock recovery image and, if possible, back up the device-specific partitions (`boot`, `config`, `rom`, `romfile`, `radio`).
