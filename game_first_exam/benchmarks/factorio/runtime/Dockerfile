ARG UPSTREAM_IMAGE
FROM ${UPSTREAM_IMAGE}
# v0.4.3 imports a2a.types.TextPart, which was removed in a2a-sdk 1.x.
RUN /opt/fle-venv/bin/pip install --no-cache-dir "a2a-sdk==0.3.22" "inspect-ai==0.3.139" \
    && /opt/fle-venv/bin/python -c "from fle.eval.inspect.integration.scorers import comprehensive_factorio_scorer; from fle.eval.tasks import TaskFactory; t = TaskFactory.create_task('iron_plate_throughput'); assert (t.trajectory_length, t.quota, t.throughput_entity) == (64, 16, 'iron-plate')"
