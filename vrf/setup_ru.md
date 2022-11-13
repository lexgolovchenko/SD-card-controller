
Для верификации будем использовать связку IcarusVerilog и библиотеки CocoTB.
Это OpenSource интструменты
Python выглядит удобным и перспективным языком для верификации.
Мне это просто интересно, давно хотел попробовать :)

## Рабочее окружение

Прямо сейчас я использую Ubuntu LTS 2020.
Но инструкция будет справедлива для любого дистрибутива Linux, и скорее всего для WSL подсистемы в Windows

## Установка IcarusVerilog

Лучше взять последнюю версию Icarus из репозитория на GitHub.
Чем новее версия, тем лучше поддержка SystemVerilog.
Хотя нас интересуте в основном синтезируемое подмножество для описания RTL, но для него в SystemVerilog добавлено
так же много интересных и удобных конструкций, от которых не хотелось бы отказываться.

Руководство по установке c GitHub тут https://steveicarus.github.io/iverilog/usage/installation.html
Там написано, как установить стабильную 11 версию. Но я буду работать с последней.

```
git clone https://github.com/steveicarus/iverilog.git
cd iverilog
sh autoconf.sh
./configure --prefix=/my/special/directory
make
```

## Установка CocoTB

Подробное руководство по установке CocoTB можно прочитать тут https://docs.cocotb.org/en/stable/install.html

Для работы с CocoTB потребуется:
- GNU Make 3+
- Python 3.6+
- Система управления пакетами Python PIP

```
sudo apt-get install make python3 python3-pip
pip3 install cocotb
```