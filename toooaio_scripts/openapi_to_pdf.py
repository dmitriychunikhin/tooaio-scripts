from typing import Any, Self

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.colors import Color, HexColor, white, black
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

from reportlab.platypus import (
    Flowable,
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    # HRFlowable,
    XPreformatted,
    KeepTogether,
    IndexingFlowable,
)
from reportlab.platypus.flowables import KeepTogetherSplitAtTop
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import glob


def openapi_i18n(term: str) -> str:
    voc = {
        "Successful Response": "Успешный ответ",
        "Validation Error": "Ошибка валидации",
    }
    return voc.get(term.strip(), term)


def create_default_font() -> str:
    script_folder = os.path.dirname(__file__)
    font_dirs = [script_folder]
    found = {}
    for fd in font_dirs:
        for f in glob.glob(os.path.join(fd, "./assets/**/*.ttf"), recursive=True):
            name = os.path.basename(f).lower()
            found[name] = f

    regular = found.get("KurintoSans-Rg.ttf".lower())
    bold = found.get("KurintoSans-Bd.ttf".lower())
    italic = found.get("KurintoSansSC-It.ttf".lower())
    bolditalic = found.get("KurintoSans-BdIt.ttf".lower())

    if regular:
        pdfmetrics.registerFont(TTFont("DefaultFont", regular))
        pdfmetrics.registerFont(TTFont("DefaultFont-Bold", bold or regular))
        pdfmetrics.registerFont(TTFont("DefaultFont-Italic", italic or regular))
        pdfmetrics.registerFont(TTFont("DefaultFont-BoldItalic", bolditalic or regular))
        from reportlab.lib.fonts import addMapping

        addMapping("DefaultFont", 0, 0, "DefaultFont")
        addMapping("DefaultFont-Bold", 1, 0, "DefaultFont-Bold")
        addMapping("DefaultFont-Italic", 0, 1, "DefaultFont-Italic")
        addMapping("DefaultFont-BoldItalic", 1, 1, "DefaultFont-BoldItalic")
        return "DefaultFont"

    return "Helvetica"


DEFAULT_FONT = create_default_font()

# --- Colors ---
PRIMARY = HexColor("#1a3a5c")
ACCENT = HexColor("#2980b9")
LIGHT_BG = HexColor("#f0f4f8")
BORDER = HexColor("#bdc3c7")
METHOD_POST = HexColor("#49cc90")
METHOD_POST_BG = HexColor("#e8f8f0")
TYPE_COLOR = HexColor("#e67e22")
REQUIRED_COLOR = HexColor("#e74c3c")
GRAY_TEXT = HexColor("#7f8c8d")
LINK_TEXT = HexColor("#2980b9")

# --- Styles ---
styles = getSampleStyleSheet()


def make_style(name: str, parent: str = "Normal", **kwargs: Any) -> ParagraphStyle:  # noqa ANN401
    base = styles[parent]
    return ParagraphStyle(
        name,
        parent=base,
        fontName=kwargs.get("fontName", DEFAULT_FONT),
        **{k: v for k, v in kwargs.items() if k != "fontName"},
    )


title_style = make_style(
    "DocTitle",
    fontSize=26,
    leading=32,
    textColor=PRIMARY,
    fontName=f"{DEFAULT_FONT}-Bold" if DEFAULT_FONT != "Helvetica" else "Helvetica-Bold",
    alignment=TA_CENTER,
    spaceAfter=6,
)
subtitle_style = make_style(
    "DocSubtitle", fontSize=12, leading=16, textColor=GRAY_TEXT, alignment=TA_CENTER, spaceAfter=30
)
h1_style = make_style(
    "H1Custom",
    fontSize=18,
    leading=22,
    textColor=PRIMARY,
    fontName=f"{DEFAULT_FONT}-Bold" if DEFAULT_FONT != "Helvetica" else "Helvetica-Bold",
    spaceBefore=20,
    spaceAfter=10,
)
h2_style = make_style(
    "H2Custom",
    fontSize=14,
    leading=18,
    textColor=ACCENT,
    fontName=f"{DEFAULT_FONT}-Bold" if DEFAULT_FONT != "Helvetica" else "Helvetica-Bold",
    spaceBefore=14,
    spaceAfter=6,
)
h3_style = make_style(
    "H3Custom",
    fontSize=11,
    leading=14,
    textColor=PRIMARY,
    fontName=f"{DEFAULT_FONT}-Bold" if DEFAULT_FONT != "Helvetica" else "Helvetica-Bold",
    spaceBefore=10,
    spaceAfter=4,
)
body_style = make_style("BodyCustom", fontSize=9.5, leading=13, textColor=black, spaceAfter=4, alignment=TA_JUSTIFY)
small_style = make_style("SmallCustom", fontSize=8, leading=10, textColor=GRAY_TEXT)
code_style = make_style(
    "CodeCustom",
    fontSize=8.5,
    leading=11,
    textColor=HexColor("#2c3e50"),
    backColor=LIGHT_BG,
    leftIndent=10,
    rightIndent=10,
    spaceBefore=4,
    spaceAfter=4,
)

link_style = make_style("LinkCustom", fontSize=8, leading=10, textColor=GRAY_TEXT)

bold_font = f"{DEFAULT_FONT}-Bold" if DEFAULT_FONT != "Helvetica" else "Helvetica-Bold"

BOLD = bold_font
REGULAR = DEFAULT_FONT


class DocSummaryFlowable(IndexingFlowable):
    def __init__(self) -> None:
        super().__init__()
        self.page_count = -1
        self._page_count = -1
        self.target = self.__class__.__qualname__

    def isSatisfied(self) -> int:
        return self._page_count > -1

    def notify(self, kind: str, stuff: Any) -> None:  # noqa ANN401
        if kind != self.target:
            return
        self.page_count = stuff.get("page_count", 0)

    def beforeBuild(self) -> None:
        self._page_count = self.page_count

    def draw(self) -> None:
        return


class CustomDocTemplateHeaderFooter:
    def __init__(self, header_left: str, footer_left: str) -> None:
        self.header_left = header_left
        self.footer_left = footer_left


class CustomDocTemplate(SimpleDocTemplate):
    def __init__(
        self,
        *args: Any,  # noqa ANN401
        header_footer_tmpl: CustomDocTemplateHeaderFooter,
        **kwargs: Any,  # noqa ANN401
    ) -> None:
        super().__init__(*args, **kwargs)
        self.header_footer_tmpl = header_footer_tmpl
        self.doc_summary = DocSummaryFlowable()

    def afterPage(self) -> None:
        if self.page > self.doc_summary.page_count:
            self.notify(self.doc_summary.target, {"page_count": self.page})

        self.draw_header_footer()

    def draw_header_footer(self) -> None:
        doc = self
        canvas = self.canv
        canvas.saveState()
        canvas.setStrokeColor(PRIMARY)

        # Header
        canvas.setLineWidth(0.5)
        canvas.line(20 * mm, A4[1] - 15 * mm, A4[0] - 20 * mm, A4[1] - 15 * mm)
        canvas.setFont(REGULAR, 7)
        canvas.setFillColor(GRAY_TEXT)
        canvas.drawString(20 * mm, A4[1] - 13 * mm, self.header_footer_tmpl.header_left or "")

        # Footer
        canvas.line(20 * mm, 15 * mm, A4[0] - 20 * mm, 15 * mm)
        canvas.drawRightString(A4[0] - 20 * mm, 10 * mm, f"Страница {doc.page} из {doc.doc_summary.page_count}")
        canvas.drawString(20 * mm, 10 * mm, self.header_footer_tmpl.footer_left or "")
        canvas.restoreState()

    def customBuild(self, story: list[Flowable]) -> None:
        story.append(self.doc_summary)
        super().multiBuild(story)


class BookmarkFlowable(Flowable):
    title: str
    key: str
    level: int

    def __init__(self, title: str, key: str, level: int) -> None:
        super().__init__()
        self.title = title
        self.key = key
        self.level = level

    def draw(self) -> None:
        curMatrixField = "_currentMatrix"
        curMatrix = (getattr(self.canv, curMatrixField) or (0,)) + (0,) * 16
        self.canv.bookmarkPage(self.key, fit="XYZ", left=0, top=curMatrix[5], zoom=None)
        self.canv.addOutlineEntry(self.title, self.key, level=self.level, closed=False)


class TOC_ITEM:
    num: int
    title: str
    level: int
    bookmark: BookmarkFlowable
    parent_item: Self | None
    nested_toc: list[Self]
    full_num: str

    def __init__(self, parent_item: Self | None, title: str) -> None:
        self.parent_item = parent_item
        self.title = title
        prev_item: Self | None = (
            (self.parent_item.nested_toc)[-1] if self.parent_item and self.parent_item.nested_toc else None
        )
        self.nested_toc = []
        self.num = (prev_item.num if prev_item else 0) + 1

        if self.parent_item:
            self.parent_item.nested_toc += [self]

        self.level = 0
        self.full_num = str(self.num)
        self.key = str(self.num)
        item = self.parent_item
        while item and item.parent_item:
            self.level += 1
            self.full_num = str(item.num) + "." + self.full_num
            self.key = str(item.num) + "_" + self.key
            item = item.parent_item

        self.key = "section_" + self.key

        self.bookmark = BookmarkFlowable(title=self.title, key=self.key, level=self.level)


def add_to_toc(story: list[Flowable], parent_item: TOC_ITEM, title: str) -> TOC_ITEM:
    toc_item = TOC_ITEM(parent_item=parent_item, title=title)
    story.append(toc_item.bookmark)
    return toc_item


def bold(text: str) -> str:
    return f'<font name="{BOLD}">{text}</font>'


def colored(text: str, color: Color) -> str:
    return f'<font color="{color}">{text}</font>'


def method_badge(method: str) -> str:
    return f'<font name="{BOLD}" color="#ffffff" backColor="{METHOD_POST}">&nbsp;{method.upper()}&nbsp;</font>'


def bookmark_link(key: str, content: str) -> str:
    return f'<a href="#{key}">{content}</a>'


def model_link_name(model_name: str) -> str:
    return f'<a name="models_{model_name}"/>' if model_name else ""


def model_link_href(model_ref: str) -> str:
    model_name = (model_ref or "").split("/")[-1]
    return f'<a href="#models_{model_name}">{model_name}</a>' if model_ref else ""


def section_toc(doc_toc: TOC_ITEM) -> list[Flowable]:
    story: list[Flowable] = []
    story.append(PageBreak())
    story.append(Paragraph("Содержание", h1_style))
    story.append(Spacer(1, 10))

    def toc_walker(parent_item: TOC_ITEM, level: int) -> None:
        indent = 20 * level
        style = make_style(f"TOC{level}", fontSize=10, leading=16, leftIndent=indent)
        for toc_item in parent_item.nested_toc:
            story.append(Paragraph(f"{bold(toc_item.full_num)} {bookmark_link(toc_item.key, toc_item.title)}", style))
            toc_walker(toc_item, level + 1)

    toc_walker(parent_item=doc_toc, level=0)

    return story


def section_title(openapi_info: dict[str, Any]) -> list[Flowable]:
    story: list[Flowable] = []
    story.append(Spacer(1, 60))
    story.append(Paragraph(openapi_info.get("title", ""), title_style))
    # story.append(Paragraph("Документация REST API v1.0.0", subtitle_style))
    # story.append(Spacer(1, 20))
    # story.append(HRFlowable(width="60%", thickness=1, color=ACCENT, spaceAfter=20, spaceBefore=10))
    story.append(
        Paragraph(
            openapi_info.get("description", ""),
            make_style("CenterBody", fontSize=11, leading=15, alignment=TA_CENTER, textColor=PRIMARY),
        )
    )
    story.append(Spacer(1, 10))
    story.append(
        Paragraph(
            f"Версия API: {openapi_info.get('version', 'н/у')}",
            make_style("CenterBody2", fontSize=11, leading=15, alignment=TA_CENTER, textColor=PRIMARY),
        )
    )

    # story.append(Spacer(1, 40))
    # info_data = [
    #     #[Paragraph(bold("Параметр"), small_style), Paragraph(bold("Значение"), small_style)],
    #     [],
    #     ["Версия API", openapi_info.get("version", "н/у")],
    #     # ["Дата создания", "JSON (application/json)"],
    #     # ["Дата изменения", "POST"],
    # ]
    # info_table = Table(info_data, colWidths=[150, 300], rowHeights=[0, None])
    # info_table.setStyle(
    #     TableStyle(
    #         [
    #             ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
    #             ("TEXTCOLOR", (0, 0), (-1, 0), white),
    #             ("FONTNAME", (0, 0), (-1, -1), REGULAR),
    #             ("FONTSIZE", (0, 0), (-1, -1), 9),
    #             #("GRID", (0, 0), (-1, -1), 0.5, BORDER),
    #             ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, LIGHT_BG]),
    #             ("TOPPADDING", (0, 0), (-1, -1), 5),
    #             ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    #             ("LEFTPADDING", (0, 0), (-1, -1), 8),
    #             ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
    #             ('ALIGN', (1, 0), (-1, -1), 'LEFT'),
    #         ]
    #     )
    # )
    # story.append(info_table)
    return story


def section_overview(parent_toc: TOC_ITEM) -> list[Flowable]:
    return []
    # story: list[Flowable] = []
    # story.append(PageBreak())
    # section_toc = add_to_toc(story, parent_toc, "Обзор API")

    # story.append(Paragraph(f"{section_toc.full_num} {section_toc.title}", h1_style))
    # story.append(
    #     Paragraph(
    #         "Данный API обеспечивает автоматизированный обмен данными между системами "
    #         "Интеграция реализована в формате REST API с передачей данных "
    #         "в формате JSON. Все операции используют метод POST.",
    #         body_style,
    #     )
    # )
    # story.append(Spacer(1, 6))
    # story.append(Paragraph(bold("Основные направления обмена:"), body_style))
    # flows = [
    #     ("ОТТУДА → СЮДА", "Передача чего-то оттуда сюда"),
    #     ("ОТСЮДА → ТУДА", "Передача чего-то отсюда туда"),
    # ]
    # flow_data = [
    #     [Paragraph(bold("Направление"), small_style), Paragraph(bold("Данные"), small_style)],
    # ]
    # for direction, data in flows:
    #     flow_data.append(
    #         [
    #             Paragraph(direction, small_style),
    #             Paragraph(data, small_style),
    #         ]
    #     )
    # ft = Table(flow_data, colWidths=[150, 305])
    # ft.setStyle(
    #     TableStyle(
    #         [
    #             ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
    #             ("TEXTCOLOR", (0, 0), (-1, 0), white),
    #             ("FONTNAME", (0, 0), (-1, -1), REGULAR),
    #             ("FONTSIZE", (0, 0), (-1, -1), 9),
    #             ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
    #             ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, LIGHT_BG]),
    #             ("TOPPADDING", (0, 0), (-1, -1), 5),
    #             ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    #             ("LEFTPADDING", (0, 0), (-1, -1), 8),
    #         ]
    #     )
    # )
    # story.append(ft)
    # story.append(Spacer(1, 10))
    # return story


def section_operations(
    parent_toc: TOC_ITEM, openapi_endpoints: dict[str, Any], openapi_schemas: dict[str, Any]
) -> list[Flowable]:

    story: list[Flowable] = []
    story.append(PageBreak())

    section_toc = add_to_toc(story, parent_toc, title="Операции")
    story.append(Paragraph(f"{section_toc.full_num} {section_toc.title}", h1_style))

    operations = []
    for endpoint_path, endpoint in openapi_endpoints.items():
        for method, operation in endpoint.items():
            operations.append(
                {
                    "path": endpoint_path,
                    "method": method.upper(),
                    "summary": operation.get("summary", ""),
                    "description": operation.get("description", ""),
                    "request_body": operation.get("requestBody"),
                    "responses": operation.get("responses"),
                }
            )

    for op in operations:
        story.append(Spacer(1, 8))

        op_title = op.get("summary", "") or op.get("path", "")

        op_story_begin: list[Flowable] = []
        op_toc = add_to_toc(op_story_begin, section_toc, op_title)

        op_story_begin.append(
            Paragraph(f'{op_toc.full_num} &nbsp;<font name="{BOLD}" color="{PRIMARY}">{op_title}</font>', h2_style)
        )
        op_story_begin.append(Paragraph(op.get("description", ""), body_style))

        op_story_begin.append(Spacer(1, 4))

        op_story_begin.append(Paragraph(f"Путь: {bold(op['path'])}", body_style))
        op_story_begin.append(Paragraph(f"Метод запроса: {method_badge(op['method'])}", body_style))

        story.append(KeepTogether(op_story_begin))

        if (op.get("request_body") or {}).get("content"):
            request_body = op["request_body"]["content"]
            for media_type, media_dict in request_body.items():
                if media_type:
                    story.append(Paragraph(f"Формат данных запроса: {bold(media_type)}", body_style))
                schema = media_dict.get("schema", {})
                model_ref = schema.get("$ref", "")
                if model_ref:
                    model_link = model_link_href(model_ref)
                    story.append(Paragraph(f"Контракт данных запроса: {colored(model_link, LINK_TEXT)}", body_style))

        ##############################################
        story.append(Spacer(1, 6))
        responses: dict[str, Any] = op.get("responses", {})
        story.append(Paragraph(bold("Ответы:"), body_style))

        for status_code, response in responses.items():
            story.append(Paragraph(f"{bold(openapi_i18n(response.get('description', '')))}", body_style))
            story.append(Paragraph(f"Код статуса: {bold(status_code)}", body_style))

            if response.get("content"):
                response_body = response["content"]
                for media_type, media_dict in response_body.items():
                    if media_type:
                        story.append(Paragraph(f"Формат данных ответа: {bold(media_type)}", body_style))
                    schema = media_dict.get("schema", {})
                    model_ref = schema.get("$ref", "")
                    if model_ref:
                        model_link = model_link_href(model_ref)
                        story.append(Paragraph(f"Контракт данных ответа: {colored(model_link, LINK_TEXT)}", body_style))

                    additional_props = schema.get("additionalProperties", "")
                    if not model_ref and additional_props:
                        story.append(
                            Paragraph(
                                f"Контракт данных ответа: {colored(additional_props.get('type', ''), TYPE_COLOR)}",
                                body_style,
                            )
                        )

            story.append(Spacer(1, 6))

        story.append(Spacer(1, 6))
        # story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=6))

    return story


def section_models(parent_toc: TOC_ITEM, openapi_schemas: dict[str, Any]) -> list[Flowable]:

    def build_field_type_span(type_schema: dict[str, Any], level: int = 0) -> str:
        res = []
        type_name = type_schema.get("type", "")
        type_fullname = type_name

        if type_schema.get("type_union"):
            type_fullname = ""
            type_union = type_schema["type_union"]
            for ti, t in enumerate(type_union, start=1):
                t_span = ""
                t_span += build_field_type_span(t, level + 1 if len(type_union) > 1 else level)
                if ti < len(type_union):
                    t_span += ", "
                res.append(t_span)

        if type_schema.get("fmt"):
            type_fullname += f""" ({type_schema["fmt"]})"""

        if type_fullname:
            res.append(colored(type_fullname, TYPE_COLOR))

        if type_schema.get("enum"):
            res.append(f"[{', '.join(str(e) for e in type_schema['enum'])}]")
        if type_schema.get("const"):
            res.append(f"(константа: {type_schema['const']})")

        ref = type_schema.get("$ref", "")
        model_link = model_link_href(ref)
        if model_link:
            res.append(model_link)

        return "<br/>".join(res)

    def build_field_table(fields: list[dict[str, Any]]) -> Table:
        header = [
            Paragraph(bold("Поле"), small_style),
            Paragraph(bold("Тип"), small_style),
            Paragraph(bold("Обяз."), small_style),
            Paragraph(bold("Описание"), small_style),
            Paragraph(bold("Пример"), small_style),
        ]
        data = [header]
        for f in fields:
            name = f["name"]
            required = bool(f.get("required"))
            desc = f.get("description", "")
            example = str(f.get("example", ""))

            type_schema = f.get("type_schema", {"type": "string"})

            data.append(
                [
                    XPreformatted(name, small_style),
                    Paragraph(build_field_type_span(type_schema), small_style),
                    Paragraph(colored("Да", REQUIRED_COLOR) if required else "Нет", small_style),
                    Paragraph(desc, small_style),
                    Paragraph(f'<font name="{REGULAR}" size="7">{example}</font>', small_style),
                ]
            )

        col_widths: list[float | None] = [None, None, 30, None, None]
        for r in data:
            w = r[0].minWidth() + 10
            col_widths[0] = max(col_widths[0] or 0, w)

            w = r[1].minWidth() + 10
            col_widths[1] = max(col_widths[1] or 0, w)

        t = Table(data, colWidths=col_widths, repeatRows=1)
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), white),
                    ("FONTNAME", (0, 0), (-1, -1), REGULAR),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("LEADING", (0, 0), (-1, -1), 10),
                    ("ALIGN", (2, 0), (2, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, LIGHT_BG]),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        return t

    def parse_prop_type(obj_schema: dict[str, Any]) -> dict[str, Any]:

        ftype = obj_schema.get("type", "")

        ftype_union = []
        if "anyOf" in obj_schema:
            ftype = "anyOf"
            types = obj_schema["anyOf"]
            for t in types:
                if t.get("type") == "null" and len(types) > 1:
                    continue
                ftype_union.append(parse_prop_type(t))

        fref = ""
        if ftype == "array" and "items" in obj_schema and "$ref" in obj_schema["items"]:
            fref = obj_schema["items"]["$ref"]
        if not fref and "$ref" in obj_schema:
            fref = obj_schema["$ref"]

        fmt = obj_schema.get("format", "")
        pattern = str(obj_schema.get("pattern") or "")

        enum = []
        if "enum" in obj_schema:
            enum = [str(e) for e in obj_schema["enum"]]

        const = str(obj_schema.get("const") or "")

        return {
            "type": ftype,
            "type_union": ftype_union,
            "$ref": fref,
            "fmt": fmt,
            "pattern": pattern,
            "enum": enum,
            "const": const,
        }

    def parse_schema_fields(schema: dict[str, Any]) -> list[dict[str, Any]]:
        fields = []
        props = schema.get("properties", {})
        req_set = set(schema.get("required", []))
        for name, prop in props.items():
            type_schema = parse_prop_type(prop)
            examples = prop.get("examples", [])
            example = examples[0] if examples else ""

            fields.append(
                {
                    "name": name,
                    "type_schema": type_schema,
                    "required": name in req_set,
                    "description": prop.get("description", ""),
                    "example": example,
                }
            )
        return fields

    def build_models() -> list[Flowable]:
        story: list[Flowable] = []
        story.append(PageBreak())

        section_toc = add_to_toc(story, parent_toc, title="Контракты данных")
        story.append(Paragraph(f"{section_toc.full_num} {section_toc.title}", h1_style))

        schemas = openapi_schemas

        for schema_name, schema in schemas.items():
            title = (schema_name + " — " + schema.get("description", "")).rstrip(" —")

            schema_toc = add_to_toc(story, section_toc, title)

            schema_story: list[Flowable] = []
            schema_story.append(Spacer(1, 8))
            schema_story.append(Paragraph(f"{model_link_name(schema_name)}{schema_toc.full_num}. {title}", h2_style))
            schema_story.append(Spacer(1, 4))

            fields = parse_schema_fields(schema)
            if fields:
                schema_story.append(build_field_table(fields))
            schema_story.append(Spacer(1, 6))

            story.append(KeepTogetherSplitAtTop(schema_story))

        return story

    return build_models()


def build_pdf(openapi_dict: dict[str, Any], output_path: str) -> None:
    openapi_info = openapi_dict.get("info", {})
    openapi_endpoints = openapi_dict.get("paths", {})
    openapi_schemas = openapi_dict.get("components", {}).get("schemas", {})

    # output_path = output_path + "/" + openapi_info.get("title", "") + " v" + openapi_info.get("version", "") + ".pdf"
    header_left = openapi_info.get("title", "") + " | API v" + openapi_info.get("version", "")
    footer_left = ""

    header_footer_tmpl = CustomDocTemplateHeaderFooter(header_left=header_left, footer_left=footer_left)

    doc = CustomDocTemplate(
        output_path,
        header_footer_tmpl=header_footer_tmpl,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=22 * mm,
        bottomMargin=22 * mm,
    )

    doc_toc = TOC_ITEM(None, "")

    sections: list[list[Flowable]] = []
    sections.append(section_title(openapi_info=openapi_info))
    sections.append(section_overview(parent_toc=doc_toc))
    sections.append(
        section_operations(parent_toc=doc_toc, openapi_endpoints=openapi_endpoints, openapi_schemas=openapi_schemas)
    )

    sections.append(section_models(parent_toc=doc_toc, openapi_schemas=openapi_schemas))

    sections.insert(1, section_toc(doc_toc=doc_toc))

    story: list[Flowable] = []
    for s in sections:
        story += s

    doc.customBuild(story)
