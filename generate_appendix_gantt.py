from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import xlsxwriter
MONTHS_RU = {
    1: "Январь",
    2: "Февраль",
    3: "Март",
    4: "Апрель",
    5: "Май",
    6: "Июнь",
    7: "Июль",
    8: "Август",
    9: "Сентябрь",
    10: "Октябрь",
    11: "Ноябрь",
    12: "Декабрь",
}
HOLIDAYS = {
    "23.02.2026",
    "08.03.2026",
    "01.05.2026",
    "09.05.2026",
    "12.06.2026",
}


@dataclass
class PlanRow:
    name: str
    start: datetime | None
    end: datetime | None
    days: int | None
    performers: str
    is_section: bool = False


def parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%d.%m.%Y")


def section(name: str) -> PlanRow:
    return PlanRow(name=name, start=None, end=None, days=None, performers="", is_section=True)


def task(name: str, start: str, end: str, days: int, performers: str) -> PlanRow:
    return PlanRow(name=name, start=parse_date(start), end=parse_date(end), days=days, performers=performers)


def reference_rows_2024() -> list[PlanRow]:
    return [
        section("1 Формирование требований к проекту"),
        task(
            "1.1 Обследование объекта и обоснование необходимости создания проекта",
            "09.02.2026",
            "10.02.2026",
            2,
            "Руководитель отдела организации мероприятий Руководитель ВКР Разработчик проекта",
        ),
        task(
            "1.2 Формирование требований пользователя к проекту",
            "11.02.2026",
            "11.02.2026",
            1,
            "Руководитель отдела организации мероприятий Руководитель ВКР Разработчик проекта",
        ),
        task("1.3 Оформление отчета о выполненной работе", "12.02.2026", "12.02.2026", 1, "Разработчик проекта"),
        section("2. Разработка концепции проекта"),
        task("2.1 Изучение объекта", "13.02.2026", "14.02.2026", 2, "Разработчик проекта"),
        task("2.2 Проведение необходимых исследовательских работ", "16.02.2026", "17.02.2026", 2, "Разработчик проекта"),
        task(
            "2.3 Разработка вариантов концепции ИТ-решения, выбор и согласование варианта, удовлетворяющего требованиям",
            "18.02.2026",
            "19.02.2026",
            2,
            "Руководитель отдела организации мероприятий Руководитель ВКР Разработчик проекта",
        ),
        task("2.4 Оценка рисков проекта", "20.02.2026", "21.02.2026", 1, "Разработчик проекта"),
        task("2.5 Оформление отчета о выполненной работе", "24.02.2026", "24.02.2026", 1, "Разработчик проекта"),
        section("3. Техническое задание"),
        task(
            "3.1 Разработка и утверждение технического задания на ИТ-решение",
            "25.02.2026",
            "26.02.2026",
            2,
            "Руководитель отдела организации мероприятий Разработчик проекта",
        ),
        task("3.2. Разработка документации", "27.02.2026", "28.02.2026", 2, "Разработчик проекта"),
        section("4. Эскизный (пилотный) проект"),
        task("4.1 Разработка предварительных проектных решений", "02.03.2026", "19.03.2026", 16, "Разработчик проекта"),
        task("4.2 Разработка программного кода ИТ-решения", "20.03.2026", "10.04.2026", 19, "Разработчик проекта"),
        task("4.3 Разработка документации на ИТ-решение и его части", "11.04.2026", "15.04.2026", 4, "Разработчик проекта"),
        section("5. Технический проект"),
        task("5.1 Разработка итоговых проектных решений", "16.04.2026", "29.04.2026", 12, "Руководитель отдела организации мероприятий Разработчик проекта"),
        task("5.2 Разработка итоговой архитектуры ИТ-решения", "30.04.2026", "16.05.2026", 13, "Разработчик проекта"),
        task("5.3 Доработка программного кода ИТ-решения", "18.05.2026", "02.06.2026", 14, "Разработчик проекта"),
        task("5.4 Разработка документации на ИТ-решение и его части", "03.06.2026", "06.06.2026", 4, "Разработчик проекта"),
        section("6. Рабочая документация"),
        task("6.1 Разработка рабочей документации на ИТ-решение", "08.06.2026", "15.06.2026", 6, "Разработчик проекта"),
        task("6.2 Формирование комплекта рабочей документации на ИТ-решение", "16.06.2026", "19.06.2026", 4, "Разработчик проекта"),
        task("6.3 Расчет затрат на проведение работ", "20.06.2026", "25.06.2026", 5, "Разработчик проекта"),
        section("7. Ввод в действие"),
        task(
            "7.1 Подготовка объекта автоматизации к вводу ИТ-решения в действие",
            "26.06.2026",
            "29.06.2026",
            3,
            "Руководитель отдела организации мероприятий Разработчик проекта",
        ),
        task("7.2 Обучение персонала", "30.06.2026", "01.07.2026", 2, "Разработчик проекта"),
        task("7.3 Комплектация ИТ-решения поставляемыми изделиями", "02.07.2026", "03.07.2026", 2, "Разработчик проекта"),
        task("7.4 Развертывание ИТ-решения", "04.07.2026", "07.07.2026", 3, "Разработчик проекта"),
        task("7.5 Тестирование ИТ-решения", "08.07.2026", "10.07.2026", 3, "Разработчик проекта"),
        task("7.6 Ввод ИТ-решения в эксплуатацию", "11.07.2026", "16.07.2026", 5, "Разработчик проекта"),
        task(
            "7.7 Проведение приемочных испытаний",
            "17.07.2026",
            "21.07.2026",
            4,
            "Руководитель отдела организации мероприятий Руководитель ВКР Разработчик проекта",
        ),
        task("7.8 Сопровождение апробации ИТ-решения", "22.07.2026", "29.07.2026", 7, "Разработчик проекта"),
    ]


def daterange(start: datetime, end: datetime) -> list[datetime]:
    days: list[datetime] = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    return days


def is_non_working_day(day: datetime) -> bool:
    return day.weekday() == 6 or day.strftime("%d.%m.%Y") in HOLIDAYS


def add_formats(workbook: xlsxwriter.Workbook) -> dict[str, xlsxwriter.format.Format]:
    border = 1
    return {
        "header": workbook.add_format(
            {
                "bold": True,
                "align": "center",
                "valign": "vcenter",
                "text_wrap": True,
                "border": border,
                "bg_color": "#D9EAF7",
                "font_size": 9,
            }
        ),
        "month": workbook.add_format(
            {"bold": True, "align": "center", "valign": "vcenter", "border": border, "bg_color": "#BDD7EE", "font_size": 8}
        ),
        "section_left": workbook.add_format(
            {
                "bold": True,
                "align": "left",
                "valign": "vcenter",
                "text_wrap": True,
                "border": border,
                "bg_color": "#E7E6E6",
                "font_size": 8,
            }
        ),
        "section": workbook.add_format(
            {"bold": True, "align": "center", "valign": "vcenter", "border": border, "bg_color": "#E7E6E6", "font_size": 8}
        ),
        "cell_left": workbook.add_format(
            {"align": "left", "valign": "vcenter", "text_wrap": True, "border": border, "font_size": 8}
        ),
        "cell_center": workbook.add_format(
            {"align": "center", "valign": "vcenter", "text_wrap": True, "border": border, "font_size": 8}
        ),
        "sunday": workbook.add_format(
            {"align": "center", "valign": "vcenter", "border": border, "bg_color": "#F4F4F4", "font_size": 8}
        ),
        "gantt": workbook.add_format(
            {"align": "center", "valign": "vcenter", "border": border, "bg_color": "#5B9BD5", "font_size": 8}
        ),
    }


def write_source_sheet(workbook: xlsxwriter.Workbook, rows: list[PlanRow], formats: dict[str, xlsxwriter.format.Format]) -> None:
    ws = workbook.add_worksheet("Таблица А.1")
    headers = ["Этап", "Дата начала", "Дата окончания", "Кол-во раб. дней", "Исполнители"]

    ws.set_column("A:A", 52)
    ws.set_column("B:C", 11)
    ws.set_column("D:D", 10)
    ws.set_column("E:E", 28)
    ws.freeze_panes(1, 0)
    ws.set_landscape()
    ws.fit_to_pages(1, 0)
    ws.set_paper(9)

    for col, header in enumerate(headers):
        ws.write(0, col, header, formats["header"])

    row_idx = 1
    for row in rows:
        if row.is_section:
            ws.write(row_idx, 0, row.name, formats["section_left"])
            for col in range(1, 5):
                ws.write_blank(row_idx, col, None, formats["section"])
        else:
            ws.write(row_idx, 0, row.name, formats["cell_left"])
            ws.write(row_idx, 1, row.start.strftime("%d.%m.%Y"), formats["cell_center"])
            ws.write(row_idx, 2, row.end.strftime("%d.%m.%Y"), formats["cell_center"])
            ws.write(row_idx, 3, row.days, formats["cell_center"])
            ws.write(row_idx, 4, row.performers, formats["cell_left"])
        row_idx += 1


def write_gantt_sheet(
    workbook: xlsxwriter.Workbook,
    title: str,
    rows: list[PlanRow],
    start: datetime,
    end: datetime,
    formats: dict[str, xlsxwriter.format.Format],
) -> None:
    ws = workbook.add_worksheet(title)
    dates = daterange(start, end)

    ws.set_column("A:A", 34)
    ws.set_column("B:C", 9)
    ws.set_column("D:D", 6)
    ws.set_column("E:E", 16)
    ws.set_column(5, 5 + len(dates), 2.2)
    ws.freeze_panes(2, 5)
    ws.set_row(0, 18)
    ws.set_row(1, 16)
    ws.set_landscape()
    ws.fit_to_pages(1, 1)
    ws.set_paper(9)
    ws.center_horizontally()
    ws.repeat_rows(0, 1)

    headers = ["Этап", "Дата начала", "Дата окончания", "Дни", "Исполнители"]
    for col, header in enumerate(headers):
        ws.merge_range(0, col, 1, col, header, formats["header"])

    month_ranges: list[tuple[str, int, int]] = []
    for idx, day in enumerate(dates, start=5):
        fmt = formats["sunday"] if is_non_working_day(day) else formats["month"]
        ws.write(1, idx, day.day, fmt)
        label = f"{MONTHS_RU[day.month]} {day.year}"
        if not month_ranges or month_ranges[-1][0] != label:
            month_ranges.append((label, idx, idx))
        else:
            name, start_col, _ = month_ranges[-1]
            month_ranges[-1] = (name, start_col, idx)

    for label, start_col, end_col in month_ranges:
        ws.merge_range(0, start_col, 0, end_col, label, formats["month"])

    row_idx = 2
    for row in rows:
        ws.set_row(row_idx, 24 if row.is_section else 30)
        if row.is_section:
            ws.write(row_idx, 0, row.name, formats["section_left"])
            for col in range(1, 5 + len(dates)):
                ws.write_blank(row_idx, col, None, formats["section"])
        else:
            ws.write(row_idx, 0, row.name, formats["cell_left"])
            ws.write(row_idx, 1, row.start.strftime("%d.%m.%Y"), formats["cell_center"])
            ws.write(row_idx, 2, row.end.strftime("%d.%m.%Y"), formats["cell_center"])
            ws.write(row_idx, 3, row.days, formats["cell_center"])
            ws.write(row_idx, 4, row.performers, formats["cell_left"])

            for col_idx, day in enumerate(dates, start=5):
                if row.start <= day <= row.end:
                    fmt = formats["gantt"]
                elif is_non_working_day(day):
                    fmt = formats["sunday"]
                else:
                    fmt = formats["cell_center"]
                ws.write_blank(row_idx, col_idx, None, fmt)
        row_idx += 1


def main() -> None:
    rows = reference_rows_2024()

    output_path = Path("C:/Users/dopof/PycharmProjects/EventManagerApp/appendix_a_gantt_holidays.xlsx")
    workbook = xlsxwriter.Workbook(output_path)
    formats = add_formats(workbook)

    write_source_sheet(workbook, rows, formats)
    write_gantt_sheet(workbook, "Общий график", rows, parse_date("09.02.2026"), parse_date("29.07.2026"), formats)

    workbook.close()
    print(output_path)


if __name__ == "__main__":
    main()
