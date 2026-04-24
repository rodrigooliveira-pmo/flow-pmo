"""Enums de domínio do Flow-PMO — fonte canônica de classificações."""
from __future__ import annotations

from enum import Enum


class ServiceClass(str, Enum):
    """Classe de serviço (prioridade de fluxo) de um item de trabalho."""
    STANDARD = "Standard"
    EXPEDITE = "Expedite"
    FIXED_DATE = "Fixed Date"
    INTANGIBLE = "Intangible Job"
    HIGHEST = "Highest"


class DemandType(str, Enum):
    """Tipo de demanda categorizado para métricas de fluxo."""
    DEV = "Dev"
    SUPPORT = "Support"
    ISSUES = "Issues"
    BAU = "BAU"
    OTHER = "Other"


class StatusCategory(str, Enum):
    """Categoria de status do item no fluxo de trabalho."""
    BACKLOG = "Backlog"
    IN_PROGRESS = "Em Progresso"
    WAITING = "Waiting"
    DONE = "Concluído"
    CANCELLED = "Cancelado"
