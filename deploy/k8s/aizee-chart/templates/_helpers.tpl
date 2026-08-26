{{/* Common labels */}}
{{- define "aizee.labels" -}}
app.kubernetes.io/name: aizee
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- end -}}

{{/* Selector labels (stable, used by Deployment/Service) */}}
{{- define "aizee.selectorLabels" -}}
app.kubernetes.io/name: aizee
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/* Full image reference with pinned tag */}}
{{- define "aizee.image" -}}
{{- .Values.image.repository }}:{{- .Values.image.tag | default .Chart.AppVersion -}}
{{- end -}}
