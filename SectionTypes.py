"""
Load the section types (eddy, reattachment etc) from the input XML file
"""
from typing import Dict
from logger import Logger


def load_section_types(section_types_tree) -> Dict[int, str]:
    """
    Load the section types (eddy, reattachment etc) from the input XML file
    """

    log = Logger('Load Sections')
    sections = {int(type_tag.attrib["id"]): type_tag.attrib["title"] for type_tag in section_types_tree.iterfind('Section')}

    assert len(sections) > 0, f'{len(sections)} active section types.'
    log.info(f'{len(sections)} section types loaded from the input XML file.')

    return sections
