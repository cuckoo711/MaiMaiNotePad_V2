<template>
	<fs-page>
		<el-card class="crud-card">
			<fs-crud ref="crudRef" v-bind="crudBinding" />
		</el-card>
	</fs-page>
</template>

<script lang="ts" setup name="contentAiModel">
import { ref, onMounted } from 'vue';
import { useExpose, useCrud } from '@fast-crud/fast-crud';
import { createCrudOptions } from './crud';

// crud 初始化
const crudRef = ref();
const crudBinding = ref();
const { crudExpose } = useExpose({ crudRef, crudBinding });
const { crudOptions } = createCrudOptions({ crudExpose });
const { resetCrudOptions } = useCrud({ crudExpose, crudOptions });

onMounted(() => {
	crudExpose.doRefresh();
});
</script>

<style lang="scss" scoped>
:deep(.fs-page-content) {
	display: flex;
	flex-direction: column;
	overflow: hidden;
}

.crud-card {
	flex: 1;
	min-height: 0;
	display: flex;
	flex-direction: column;
	:deep(.el-card__body) {
		flex: 1;
		min-height: 0;
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}
}
</style>
