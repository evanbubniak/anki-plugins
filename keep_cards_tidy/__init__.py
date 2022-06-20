from aqt import gui_hooks, mw
from aqt.utils import qconnect
from aqt.qt import QAction
from typing import cast
from bs4 import BeautifulSoup

back_tags_to_purge = [f"h{i}" for i in range(1, 7)] + ["p", "span", "font"]
front_tags_to_purge = ["div", "br"] + back_tags_to_purge

def _remove_attr(soup, attr):
    for tag in soup.findAll(True):
        if tag.attrs.get(attr):
            del tag[attr]
    return soup

def _remove_all_attrs(soup, tag):
    for tag in soup.findAll(tag):
        tag.attrs.clear()
    return soup

def convert_danish_formatting():
    danish_deck_id = mw.col.decks.id_for_name("Danish")
    for is_neuter_note_id in mw.col.db.execute(f"select notes.id from notes left join cards on notes.id = cards.nid where cards.did={danish_deck_id} and substr(flds, 0, instr(flds, char(31))) like 'et %'"):
        note = mw.col.getNote(cast(int, is_neuter_note_id[0]))
        front_side = note.items()[0][0]
        note[front_side] = note[front_side][3:] + " (n)"
        note.flush()
    for is_common_note_id in mw.col.db.execute(f"select notes.id from notes left join cards on notes.id = cards.nid where cards.did={danish_deck_id} and substr(flds, 0, instr(flds, char(31))) like 'en %'"):
        note = mw.col.getNote(cast(int, is_common_note_id[0]))
        front_side = note.items()[0][0]
        note[front_side] = note[front_side][3:] + " (c)"
        note.flush()   

def clean_deck() -> None:
    if mw is not None and mw.col.db:
        # remove CSS styles from tags so they appear as unformatted text
        for has_style_note_id in mw.col.db.execute(r"select id from notes where flds like '%style=%'"):
            note = mw.col.getNote(cast(int, has_style_note_id[0]))
            for field_name in [item[0] for item in note.items()]:
                if "style=" in note[field_name]:
                    note[field_name] = str(_remove_attr(BeautifulSoup(note[field_name], "html.parser"), "style"))

            note.flush()
        # remove attributes from any <font> tags if present
        for has_font_note_id in mw.col.db.execute(r"select id from notes where flds like '%</font>%'"):
            note = mw.col.getNote(cast(int, has_font_note_id[0]))
            for field_name in [item[0] for item in note.items()]:
                if "</font>" in note[field_name]:
                    note[field_name] = str(_remove_all_attrs(BeautifulSoup(note[field_name], "html.parser"), "font"))
                    note[field_name] = note[field_name].replace("<font>", "")
                    note[field_name] = note[field_name].replace("</font>", "")
            note.flush()

        # remove classes from tags
        for has_class_note_id in mw.col.db.execute(r"select id from notes where flds like '%class=%'"):
            note = mw.col.getNote(cast(int, has_class_note_id[0]))
            for field_name in [item[0] for item in note.items()]:
                if "class=" in note[field_name]:
                    note[field_name] = str(_remove_attr(BeautifulSoup(note[field_name], "html.parser"), "class"))

            note.flush()
        # remove no-break spaces entirely from notes
        for nbsp_note_id in mw.col.db.execute("select id from notes where flds like '%&nbsp;%'"):
            note = mw.col.getNote(cast(int, nbsp_note_id[0]))
            for field_name in [item[0] for item in note.items()]:
                note[field_name] = note[field_name].replace("&nbsp;", " ")
            note.flush()
        # remove text tags, line breaks, and divs from front side of notes
        for tag in front_tags_to_purge:
            for tag_note_id in mw.col.db.execute(f"select id from notes where substr(flds, 0, instr(flds, char(31))) like '%<{tag}%>%'"):
                note = mw.col.getNote(cast(int, tag_note_id[0]))
                front_side = note.items()[0][0]
                note[front_side] = note[front_side].replace(f"<{tag}>", "")
                note[front_side] = note[front_side].replace(f"</{tag}>", "")
                note.flush()
        # remove text tags from back side of notes
        for tag in back_tags_to_purge:
            for tag_note_id in mw.col.db.execute(f"select id from notes where substr(flds, instr(flds, char(31))+1, length(flds) - instr(flds, char(31))) like '%<{tag}>%'"):
                note = mw.col.getNote(cast(int, tag_note_id[0]))
                back_side = note.items()[1][0]
                note[back_side] = note[back_side].replace(f"<{tag}>", "")
                note[back_side] = note[back_side].replace(f"</{tag}>", "")
                note.flush()
        # replace divs with line breaks in notes
        for has_div_note_id in mw.col.db.execute("select id from notes where flds like '%<div>%'"):
            note = mw.col.getNote(cast(int, has_div_note_id[0]))
            back_side = note.items()[1][0]
            note[back_side] = note[back_side].replace("<div>", "<br>")
            note[back_side] = note[back_side].replace("</div>", "")

            note.flush()
        # replace self-closed line break tags with unclosed tags so subsequent replacements can match them
        for has_self_closing_br_note_id in mw.col.db.execute("select id from notes where flds like '%<br/>%'"):
            note = mw.col.getNote(cast(int, has_self_closing_br_note_id[0]))
            back_side = note.items()[1][0]
            note[back_side] = note[back_side].replace("<br/>", "<br>")

            note.flush()
        # remove leading line breaks from the back side of notes
        for back_starts_with_br_note_id in mw.col.db.execute("select id from notes where substr(flds, instr(flds, char(31))+1, 4) = '<br>'"):
            note = mw.col.getNote(cast(int, back_starts_with_br_note_id[0]))
            back_side = note.items()[1][0]
            while note[back_side][:4] == "<br>":
                note[back_side] = note[back_side][4:]

            note.flush()
        # remove trailing line breaks from the back side of notes
        for back_ends_with_br_note_id in mw.col.db.execute("select id from notes where substr(flds, length(flds)-3, 4) = '<br>'"):
            note = mw.col.getNote(cast(int, back_ends_with_br_note_id[0]))
            back_side = note.items()[1][0]
            while note[back_side][-4:] == "<br>":
                note[back_side] = note[back_side][:-4]

            note.flush()
        # remove spaces that lead into line breaks from back side of notes
        for has_space_before_br_note_id in mw.col.db.execute("select id from notes where flds like '% <br>%'"):
            note = mw.col.getNote(cast(int, has_space_before_br_note_id[0]))
            back_side = note.items()[1][0]
            while " <br>" in note[back_side]:
                note[back_side] = note[back_side].replace(" <br>", "<br>")

            note.flush()
        # remove spaces that trail line breaks from back side of notes that do not contain code snippets
        for has_space_after_br_note_id in mw.col.db.execute("select id from notes where flds like '%<br> %' and flds not like '%<code>%'"):
            note = mw.col.getNote(cast(int, has_space_after_br_note_id[0]))
            back_side = note.items()[1][0]
            while "<br> " in note[back_side]:
                note[back_side] = note[back_side].replace("<br> ", "<br>")

            note.flush()
        # replace all instances of 3+ line breaks with double line breaks
        for has_three_consecutive_brs_note_id in mw.col.db.execute("select id from notes where flds like '%<br><br><br>%'"):
            note = mw.col.getNote(cast(int, has_three_consecutive_brs_note_id[0]))
            back_side = note.items()[1][0]
            while "<br><br><br>" in note[back_side]:
                note[back_side] = note[back_side].replace("<br><br><br>", "<br><br>")

            note.flush()
        # add <pre> tags around code tags if they are missing, so that indentation appears properly
        for has_unpreformatted_code_note_id in mw.col.db.execute("select id from notes where flds like '%<code>%' and flds not like '%<pre><code>%'"):
            note = mw.col.getNote(cast(int, has_unpreformatted_code_note_id[0]))
            for field_name in [item[0] for item in note.items()]:
                note[field_name] = note[field_name].replace("<code>", "<pre><code>")
                note[field_name] = note[field_name].replace("</code>", "</code></pre>")
            note.flush()

gui_hooks.sync_will_start.append(clean_deck)

if mw is not None:
    action = QAction("Reformat all cards", mw)
    qconnect(action.triggered, clean_deck)
    mw.form.menuTools.addAction(action)