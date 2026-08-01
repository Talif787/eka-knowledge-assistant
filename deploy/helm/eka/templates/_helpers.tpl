{{/* Chart name, overridable. */}}
{{- define "eka.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* Fully qualified app name. */}}
{{- define "eka.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "eka.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* Common labels. */}}
{{- define "eka.labels" -}}
helm.sh/chart: {{ include "eka.chart" . }}
{{ include "eka.selectorLabels" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: eka
{{- end -}}

{{/* Selector labels. */}}
{{- define "eka.selectorLabels" -}}
app.kubernetes.io/name: {{ include "eka.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "eka.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "eka.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{/* Image reference, defaulting the tag to the chart appVersion. */}}
{{- define "eka.image" -}}
{{- $tag := default .Chart.AppVersion .Values.image.tag -}}
{{- printf "%s:%s" .Values.image.repository $tag -}}
{{- end -}}

{{/* Postgres service name (in-cluster). */}}
{{- define "eka.postgresHost" -}}
{{- printf "%s-postgres" (include "eka.fullname" .) -}}
{{- end -}}

{{/* Redis service name (in-cluster). */}}
{{- define "eka.redisHost" -}}
{{- printf "%s-redis" (include "eka.fullname" .) -}}
{{- end -}}

{{/* Async database DSN. In-cluster when enabled, otherwise the external DSN. */}}
{{- define "eka.databaseDsn" -}}
{{- if .Values.postgresql.enabled -}}
{{- $a := .Values.postgresql.auth -}}
{{- printf "postgresql+asyncpg://%s:%s@%s:5432/%s" $a.username $a.password (include "eka.postgresHost" .) $a.database -}}
{{- else -}}
{{- required "externalDatabase.dsn is required when postgresql.enabled is false" .Values.externalDatabase.dsn -}}
{{- end -}}
{{- end -}}

{{/* Redis URL. In-cluster when enabled, otherwise the external URL. */}}
{{- define "eka.redisUrl" -}}
{{- if .Values.redis.enabled -}}
{{- printf "redis://%s:6379/0" (include "eka.redisHost" .) -}}
{{- else -}}
{{- required "externalRedis.url is required when redis.enabled is false" .Values.externalRedis.url -}}
{{- end -}}
{{- end -}}

{{/* JWT secret, required so an install without one fails closed. */}}
{{- define "eka.jwtSecret" -}}
{{- required "jwt.secret is required (set a strong 32+ byte value)" .Values.jwt.secret -}}
{{- end -}}

{{/* Standard env sources for app containers. */}}
{{- define "eka.envFrom" -}}
- configMapRef:
    name: {{ include "eka.fullname" . }}-config
- secretRef:
    name: {{ include "eka.fullname" . }}-secret
{{- end -}}

{{/*
Wait-for-db init container, emitted only for the in-cluster database, where the
host is known. Uses the app image (python plus sh); no extra tooling required.
*/}}
{{- define "eka.waitForDb" -}}
- name: wait-for-db
  image: {{ include "eka.image" . }}
  imagePullPolicy: {{ .Values.image.pullPolicy }}
  command:
    - sh
    - -c
    - |
      echo "waiting for database at {{ include "eka.postgresHost" . }}:5432"
      until python -c "import socket; socket.create_connection(('{{ include "eka.postgresHost" . }}', 5432), 2).close()" 2>/dev/null; do
        echo "database not ready, retrying in 2s"; sleep 2;
      done
      echo "database is ready"
  securityContext:
    {{- include "eka.containerSecurityContext" . | nindent 4 }}
{{- end -}}

{{/* Hardened container security context. */}}
{{- define "eka.containerSecurityContext" -}}
allowPrivilegeEscalation: false
readOnlyRootFilesystem: true
runAsNonRoot: true
runAsUser: 999
runAsGroup: 999
capabilities:
  drop:
    - ALL
seccompProfile:
  type: RuntimeDefault
{{- end -}}
