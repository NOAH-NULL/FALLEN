def setup_telemetry(settings):
    if not settings.otel_enabled: return
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        provider=TracerProvider(resource=Resource.create({'service.name':settings.otel_service_name,'deployment.environment':settings.environment}))
        if settings.otel_exporter_endpoint:
            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_exporter_endpoint,insecure=True)))
        trace.set_tracer_provider(provider)
    except ImportError: pass
