# 导航菜单相关 schema，由 Backend 提供给前端

from pydantic import BaseModel, Field


class MenuItem(BaseModel):
    """单个导航项"""
    id: str = Field(..., description="唯一标识")
    title: str = Field(..., description="显示名称")
    path: str = Field("", description="前端路由路径")
    icon: str | None = Field(None, description="图标名，可选")


class MenuListResponse(BaseModel):
    """导航菜单列表响应"""
    menus: list[MenuItem]
