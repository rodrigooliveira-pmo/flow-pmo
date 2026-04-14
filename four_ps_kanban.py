"""Compatibilidade para `four_ps_kanban.py` no diretório raiz.

O código real vive em `jira/four_ps_kanban.py`, mas muitos comandos usam
`python four_ps_kanban.py` a partir da raiz do repositório.
"""

from jira.four_ps_kanban import FourPsKanbanExtractor  # noqa: F401


if __name__ == "__main__":
    print("Este arquivo é um wrapper de compatibilidade para jira/four_ps_kanban.py.")
    print("Use o módulo diretamente ou execute a partir do pacote Jira:")
    print("  python -m jira.four_ps_kanban")
    print("Se você realmente precisa de um CLI, importe FourPsKanbanExtractor em um script.")
