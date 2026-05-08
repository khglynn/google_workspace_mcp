from unittest.mock import Mock

import pytest

from core.server import server
from core.utils import UserInputError
from gslides.slides_tools import batch_update_presentation

EXPECTED_SLIDES_BATCH_REQUEST_TYPES = {
    "createSlide",
    "createShape",
    "createTable",
    "insertText",
    "insertTableRows",
    "insertTableColumns",
    "deleteTableRow",
    "deleteTableColumn",
    "replaceAllText",
    "deleteObject",
    "updatePageElementTransform",
    "updateSlidesPosition",
    "deleteText",
    "createImage",
    "createVideo",
    "createSheetsChart",
    "createLine",
    "refreshSheetsChart",
    "updateShapeProperties",
    "updateImageProperties",
    "updateVideoProperties",
    "updatePageProperties",
    "updateTableCellProperties",
    "updateLineProperties",
    "createParagraphBullets",
    "replaceAllShapesWithImage",
    "duplicateObject",
    "updateTextStyle",
    "replaceAllShapesWithSheetsChart",
    "deleteParagraphBullets",
    "updateParagraphStyle",
    "updateTableBorderProperties",
    "updateTableColumnProperties",
    "updateTableRowProperties",
    "mergeTableCells",
    "unmergeTableCells",
    "groupObjects",
    "ungroupObjects",
    "updatePageElementAltText",
    "replaceImage",
    "updateSlideProperties",
    "updatePageElementsZOrder",
    "updateLineCategory",
    "rerouteLine",
}


def _unwrap(tool):
    """Unwrap FunctionTool + decorators to the original async function."""
    fn = tool.fn if hasattr(tool, "fn") else tool
    while hasattr(fn, "__wrapped__"):
        fn = fn.__wrapped__
    return fn


def _build_slides_service(presentation=None, batch_update_response=None):
    service = Mock()
    presentations = service.presentations.return_value
    presentations.get.return_value.execute.return_value = presentation or {
        "slides": [{"objectId": "p"}]
    }
    presentations.batchUpdate.return_value.execute.return_value = (
        batch_update_response or {"replies": []}
    )
    return service, presentations


@pytest.mark.asyncio
async def test_batch_update_schema_exposes_slides_request_variants():
    tools = await server.list_tools(run_middleware=False)
    tool = next(tool for tool in tools if tool.name == "batch_update_presentation")

    requests_schema = tool.parameters["properties"]["requests"]
    request_variants = requests_schema["items"]["anyOf"]
    request_types = {next(iter(variant["properties"])) for variant in request_variants}

    assert requests_schema["minItems"] == 1
    assert len(request_variants) == 44
    assert request_types == EXPECTED_SLIDES_BATCH_REQUEST_TYPES

    for variant in request_variants:
        assert variant["additionalProperties"] is False
        assert len(variant["properties"]) == 1
        request_type = next(iter(variant["properties"]))
        assert variant["required"] == [request_type]
        request_payload = variant["properties"][request_type]
        assert request_payload["additionalProperties"] is False
        assert request_payload["properties"]

    create_shape = next(
        variant["properties"]["createShape"]
        for variant in request_variants
        if "createShape" in variant["properties"]
    )
    assert create_shape["additionalProperties"] is False
    assert {
        "objectId",
        "shapeType",
        "elementProperties",
    }.issubset(create_shape["properties"])

    create_line = next(
        variant["properties"]["createLine"]
        for variant in request_variants
        if "createLine" in variant["properties"]
    )
    assert {"category", "lineCategory"}.issubset(create_line["properties"])

    replace_shapes_with_image = next(
        variant["properties"]["replaceAllShapesWithImage"]
        for variant in request_variants
        if "replaceAllShapesWithImage" in variant["properties"]
    )
    assert {"imageReplaceMethod", "replaceMethod"}.issubset(
        replace_shapes_with_image["properties"]
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("requests", "expected_message"),
    [
        ([], "requests must contain at least one request object"),
        ([{}], "requests[0] is empty"),
        ([{"unknownRequest": {}}], "unsupported request type 'unknownRequest'"),
        (
            [{"createSlide": {}, "insertText": {}}],
            "requests[0] contains multiple fields (createSlide, insertText)",
        ),
        ([{"createSlide": None}], "requests[0].createSlide must be an object"),
    ],
)
async def test_batch_update_rejects_invalid_request_objects(requests, expected_message):
    service, presentations = _build_slides_service()

    with pytest.raises(UserInputError) as exc_info:
        await _unwrap(batch_update_presentation)(
            service=service,
            user_google_email="user@example.com",
            presentation_id="presentation-1",
            requests=requests,
        )

    message = str(exc_info.value)
    assert expected_message in message
    assert "exactly one Slides request type" in message
    assert "createSlide" in message
    presentations.get.assert_not_called()
    presentations.batchUpdate.assert_not_called()


@pytest.mark.asyncio
async def test_batch_update_rejects_insert_text_targeting_slide_id():
    service, presentations = _build_slides_service()

    with pytest.raises(UserInputError) as exc_info:
        await _unwrap(batch_update_presentation)(
            service=service,
            user_google_email="user@example.com",
            presentation_id="presentation-1",
            requests=[
                {
                    "insertText": {
                        "objectId": "p",
                        "insertionIndex": 0,
                        "text": "Title",
                    }
                }
            ],
        )

    assert "requests[0].insertText.objectId='p'" in str(exc_info.value)
    assert "createShape" in str(exc_info.value)
    presentations.batchUpdate.assert_not_called()


@pytest.mark.asyncio
async def test_batch_update_rejects_insert_text_targeting_other_page_ids():
    service, presentations = _build_slides_service(
        presentation={
            "slides": [
                {
                    "objectId": "slide_1",
                    "slideProperties": {"notesPage": {"objectId": "notes_1"}},
                }
            ],
            "masters": [{"objectId": "master_1"}],
            "layouts": [{"objectId": "layout_1"}],
            "notesMaster": {"objectId": "notes_master_1"},
        }
    )

    with pytest.raises(UserInputError) as exc_info:
        await _unwrap(batch_update_presentation)(
            service=service,
            user_google_email="user@example.com",
            presentation_id="presentation-1",
            requests=[
                {
                    "insertText": {
                        "objectId": "master_1",
                        "insertionIndex": 0,
                        "text": "Title",
                    }
                },
                {
                    "insertText": {
                        "objectId": "layout_1",
                        "insertionIndex": 0,
                        "text": "Title",
                    }
                },
                {
                    "insertText": {
                        "objectId": "notes_master_1",
                        "insertionIndex": 0,
                        "text": "Title",
                    }
                },
                {
                    "insertText": {
                        "objectId": "notes_1",
                        "insertionIndex": 0,
                        "text": "Title",
                    }
                },
            ],
        )

    message = str(exc_info.value)
    assert "requests[0].insertText.objectId='master_1'" in message
    assert "requests[1].insertText.objectId='layout_1'" in message
    assert "requests[2].insertText.objectId='notes_master_1'" in message
    assert "requests[3].insertText.objectId='notes_1'" in message
    presentations.get.assert_called_once_with(
        presentationId="presentation-1",
        fields=(
            "slides(objectId,slideProperties(notesPage(objectId))),masters(objectId),layouts(objectId),notesMaster(objectId)"
        ),
    )
    presentations.batchUpdate.assert_not_called()


@pytest.mark.asyncio
async def test_batch_update_allows_insert_text_targeting_created_shape():
    service, presentations = _build_slides_service(
        batch_update_response={
            "replies": [
                {},
                {"createShape": {"objectId": "title_box"}},
                {},
            ]
        }
    )
    requests = [
        {"createSlide": {"objectId": "slide_2"}},
        {
            "createShape": {
                "objectId": "title_box",
                "shapeType": "TEXT_BOX",
                "elementProperties": {"pageObjectId": "slide_2"},
            }
        },
        {
            "insertText": {
                "objectId": "title_box",
                "insertionIndex": 0,
                "text": "Title",
            }
        },
    ]

    result = await _unwrap(batch_update_presentation)(
        service=service,
        user_google_email="user@example.com",
        presentation_id="presentation-1",
        requests=requests,
    )

    call_kwargs = presentations.batchUpdate.call_args.kwargs
    assert call_kwargs["body"] == {"requests": requests}
    assert "Batch Update Completed" in result
    assert "Created shape with ID title_box" in result


@pytest.mark.asyncio
async def test_batch_update_strips_schema_nulls_before_google_api_call():
    service, presentations = _build_slides_service(
        batch_update_response={"replies": [{"createSlide": {"objectId": "slide_2"}}]}
    )
    requests = [
        {
            "createSlide": {
                "objectId": "slide_2",
                "insertionIndex": None,
                "slideLayoutReference": None,
            }
        }
    ]

    await _unwrap(batch_update_presentation)(
        service=service,
        user_google_email="user@example.com",
        presentation_id="presentation-1",
        requests=requests,
    )

    call_kwargs = presentations.batchUpdate.call_args.kwargs
    assert call_kwargs["body"] == {
        "requests": [{"createSlide": {"objectId": "slide_2"}}]
    }


@pytest.mark.asyncio
async def test_batch_update_rejects_insert_text_targeting_new_slide_id():
    service, presentations = _build_slides_service(presentation={"slides": []})

    with pytest.raises(UserInputError) as exc_info:
        await _unwrap(batch_update_presentation)(
            service=service,
            user_google_email="user@example.com",
            presentation_id="presentation-1",
            requests=[
                {"createSlide": {"objectId": "slide_2"}},
                {
                    "insertText": {
                        "objectId": "slide_2",
                        "insertionIndex": 0,
                        "text": "Title",
                    }
                },
            ],
        )

    assert "requests[1].insertText.objectId='slide_2'" in str(exc_info.value)
    presentations.batchUpdate.assert_not_called()
