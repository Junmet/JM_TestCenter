# 系统相关接口：导航菜单等，由 Backend 提供

from fastapi import APIRouter, Depends

from app.api.deps.auth import get_current_user
from app.db.models.user import User
from app.schemas.menu import MenuItem, MenuListResponse

router = APIRouter()


@router.get("/menus", response_model=MenuListResponse)
def get_menus(_user: User = Depends(get_current_user)) -> MenuListResponse:
    """
    获取当前用户可用的导航菜单数据，供前端顶部导航栏使用。
    """
    # 后续可按用户权限过滤；此处先返回统一菜单
    menus = [
        MenuItem(id="home", title="首页", path="/home", icon="home"),
        MenuItem(id="dashboard", title="控制台", path="/dashboard", icon="dashboard"),
        MenuItem(id="cases", title="用例管理", path="/cases", icon="cases"),
        MenuItem(id="case-gen", title="用例生成", path="/case-gen", icon="case-gen"),
        MenuItem(id="ui-automation", title="UI 自动化", path="/ui-automation", icon="robot"),
        MenuItem(id="ai-chat", title="AI 对话", path="/ai-chat", icon="chat"),
    ]
    return MenuListResponse(menus=menus)
