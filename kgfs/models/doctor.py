"""Doctor-style reports for optional local model setup."""

from __future__ import annotations

from dataclasses import dataclass

from kgfs.core.config import KGFSConfig
from kgfs.models.paths import ModelPathInfo, collect_model_paths
from kgfs.models.validation import BackendValidation, validate_all_backends


@dataclass(frozen=True)
class ModelDoctorReport:
    validations: list[BackendValidation]
    paths: list[ModelPathInfo]

    @property
    def warnings(self) -> list[str]:
        values: list[str] = []
        for validation in self.validations:
            values.extend(validation.warnings)
        for path in self.paths:
            values.extend(path.warnings)
        return values


def build_model_doctor_report(config: KGFSConfig) -> ModelDoctorReport:
    return ModelDoctorReport(validate_all_backends(config), collect_model_paths(config))
