"""CSV writers: headers from dimension labels, joined ids, stream-based."""

from __future__ import annotations

import io

from pycadwork.reporting import (
    MaterialTotalRow,
    PartRow,
    by_material,
    by_storey,
    write_material_totals_csv,
    write_parts_csv,
)


def _row(group: tuple[str, ...] = ()) -> PartRow:
    return PartRow(
        group=group,
        element_type="beam",
        name="Stud",
        material_name="Pine",
        length=3000.0,
        width=80.0,
        height=200.0,
        count=3,
        total_volume=0.144,
        total_weight=72.0,
        element_ids=(1, 2, 3),
    )


def test_parts_csv_headers_and_id_join() -> None:
    stream = io.StringIO()

    write_parts_csv([_row()], stream)

    header, line = stream.getvalue().splitlines()
    assert header.startswith("element_type,name,material_name,")
    assert line == "beam,Stud,Pine,3000.0,80.0,200.0,3,0.144,72.0,1;2;3"


def test_parts_csv_prepends_one_column_per_dimension() -> None:
    stream = io.StringIO()

    write_parts_csv(
        [_row(group=("B/GF", "Pine"))],
        stream,
        dimensions=(by_storey(), by_material()),
    )

    header, line = stream.getvalue().splitlines()
    assert header.startswith("storey,material,element_type,")
    assert line.startswith("B/GF,Pine,beam,")


def test_parts_csv_generic_headers_without_dimensions() -> None:
    stream = io.StringIO()
    write_parts_csv([_row(group=("a", "b"))], stream)
    assert stream.getvalue().splitlines()[0].startswith("group_1,group_2,element_type,")


def test_material_totals_csv() -> None:
    stream = io.StringIO()

    write_material_totals_csv(
        [
            MaterialTotalRow(
                group=(),
                material_name="Pine",
                count=5,
                total_volume=0.5,
                total_weight=250.0,
            )
        ],
        stream,
    )

    assert stream.getvalue().splitlines() == [
        "material_name,count,total_volume,total_weight",
        "Pine,5,0.5,250.0",
    ]
