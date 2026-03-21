<template>
  <Codemirror
    :model-value="modelValue"
    class="pipeline-json-cm"
    placeholder="粘贴步骤 JSON，或点击「插入示例」"
    :style="editorStyle"
    :tab-size="2"
    :indent-with-tab="true"
    :extensions="extensions"
    @update:model-value="emit('update:modelValue', $event)"
  />
</template>

<script setup lang="ts">
import { computed } from "vue";
import { Codemirror } from "vue-codemirror";
import { json } from "@codemirror/lang-json";
import { EditorView } from "@codemirror/view";
import type { Extension } from "@codemirror/state";

defineProps<{
  modelValue: string;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", v: string): void;
}>();

const editorStyle = computed(() => ({
  minHeight: "320px",
  height: "min(440px, 42vh)",
  width: "100%"
}));

const extensions = computed<Extension[]>(() => [
  json(),
  EditorView.lineWrapping,
  EditorView.theme({
    "&": { fontSize: "13px" },
    ".cm-editor": {
      border: "1px solid var(--el-border-color, #dcdfe6)",
      borderRadius: "4px",
      outline: "none",
      background: "var(--el-fill-color-blank, #fff)"
    },
    ".cm-editor.cm-focused": {
      borderColor: "var(--el-color-primary, #409eff)"
    },
    ".cm-scroller": {
      fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace'
    },
    ".cm-gutters": {
      borderRight: "1px solid var(--el-border-color-lighter, #ebeef5)",
      background: "var(--el-fill-color-light, #f5f7fa)"
    }
  })
]);
</script>

<style scoped>
.pipeline-json-cm {
  width: 100%;
}
</style>
