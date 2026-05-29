import logging
from typing import Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from app.tools.campus_tools import (
    get_campus_events,
    get_course_reminders,
    get_weather_forecast,
)

logger = logging.getLogger(__name__)

router = APIRouter()

class ToolRequest(BaseModel):
    """
    Request model for the /test-mcp-tool endpoint.
    """
    tool_name: str = Field(..., description="The name of the MCP tool to run")
    tool_args: dict[str, Any] = Field(
        default_factory=dict, 
        description="The arguments to pass to the MCP tool"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "tool_name": "get_weather_forecast",
                "tool_args": {"location": "New York,US"}
            }
        }
    }

@router.post("/test-mcp-tool", status_code=status.HTTP_200_OK)
async def test_mcp_tool(request: ToolRequest) -> dict[str, Any]:
    """
    Evaluation endpoint to execute and test MCP tools.
    Supports:
      - get_campus_events
      - get_course_reminders
      - get_weather_forecast
    """
    tool_name = request.tool_name
    tool_args = request.tool_args

    logger.info(f"Received test-mcp-tool request for tool: '{tool_name}' with args: {tool_args}")

    try:
        if tool_name == "get_campus_events":
            result = await get_campus_events()
            return {"status": "success", "tool": tool_name, "result": result}

        elif tool_name == "get_course_reminders":
            program = tool_args.get("program")
            if not program:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Argument 'program' is required for tool 'get_course_reminders'."
                )
            result = await get_course_reminders(program=program)
            return {"status": "success", "tool": tool_name, "result": result}

        elif tool_name == "get_weather_forecast":
            location = tool_args.get("location")
            if not location:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Argument 'location' is required for tool 'get_weather_forecast'."
                )
            result = await get_weather_forecast(location=location)
            return {"status": "success", "tool": tool_name, "result": result}

        else:
            logger.warning(f"Attempted to run unsupported tool name: {tool_name}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported tool name: '{tool_name}'. Supported tools are: "
                       f"get_campus_events, get_course_reminders, get_weather_forecast"
            )

    except HTTPException:
        # Re-raise HTTP exceptions to let FastAPI handle them
        raise
    except Exception as e:
        logger.error(f"Error executing tool '{tool_name}' with args {tool_args}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing tool: {str(e)}"
        )
