from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import engine


def main() -> None:
    settings = get_settings()
    conn = engine.connect()
    try:
        rows = conn.execute(
            text(
                """
                select
                    table_name,
                    column_name,
                    column_comment,
                    hex(column_comment) as column_comment_hex
                from information_schema.columns
                where table_schema=:db
                  and table_name in ('users', 'refresh_tokens')
                order by table_name, ordinal_position
                """
            ),
            {"db": settings.MYSQL_DB},
        ).fetchall()

        print("columns:")
        for r in rows:
            print(
                r.table_name,
                r.column_name,
                repr(r.column_comment),
                "hex=" + str(r.column_comment_hex),
            )

        tables = conn.execute(
            text(
                """
                select table_name, table_comment, hex(table_comment) as table_comment_hex
                from information_schema.tables
                where table_schema=:db
                  and table_name in ('users', 'refresh_tokens')
                order by table_name
                """
            ),
            {"db": settings.MYSQL_DB},
        ).fetchall()

        print("tables:")
        for t in tables:
            print(t.table_name, repr(t.table_comment), "hex=" + str(t.table_comment_hex))
    finally:
        conn.close()


if __name__ == "__main__":
    main()

