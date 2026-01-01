from typing import Dict, Optional

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader


class Metrics:
    def __init__(self, is_enabled: bool, endpoint: str):
        self.enabled = is_enabled
        if self.enabled:
            # Set up OTLP gRPC exporter
            otlp_exporter = OTLPMetricExporter(endpoint=endpoint, insecure=True)
            metric_reader = PeriodicExportingMetricReader(otlp_exporter)
            provider = MeterProvider(metric_readers=[metric_reader])
            metrics.set_meter_provider(provider)
            self.meter = metrics.get_meter("dsp_api_genai")
            self._counters: Dict[str, any] = {}
            self._histograms: Dict[str, any] = {}
        else:
            self.meter = None
            self._counters = {}
            self._histograms = {}

    def record_latency(
        self,
        name: str,
        value: float,
        description: str = "",
        attributes: Optional[Dict[str, str]] = None,
    ):
        if not self.enabled:
            return
        if name not in self._histograms:
            self._histograms[name] = self.meter.create_histogram(
                name=name, description=description, unit="ms"
            )
        histogram = self._histograms[name]
        histogram.record(value, attributes or {})

    def record_event(
        self,
        name: str,
        description: str = "",
        attributes: Optional[Dict[str, str]] = None,
    ):
        if not self.enabled:
            return
        if name not in self._histograms:
            self._histograms[name] = self.meter.create_histogram(
                name=name, description=description, unit="1"
            )
        histogram = self._histograms[name]
        histogram.record(1, attributes or {})
