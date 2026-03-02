import { defineAsyncComponent, AsyncComponentLoader } from 'vue';
export let pluginsAll: any = [];
// 扫描插件目录并注册插件
export const scanAndInstallPlugins = (app: any) => {
	// 排除 api.ts 文件，只扫描组件文件
	const components = import.meta.glob('./**/*.ts');
	const pluginNames = new Set();
	const registeredComponents = new Set(); // 记录已注册的组件名，避免重复注册
	
	// 遍历对象并注册异步组件
	for (const [key, value] of Object.entries(components)) {
		const name = key.slice(key.lastIndexOf('/') + 1, key.lastIndexOf('.'));
		// 如果文件名是 api 或 index，则跳过注册，避免与业务代码冲突
		if (name === 'api' || name === 'index') continue;
		
		// 避免重复注册同名组件
		if (registeredComponents.has(name)) {
			console.warn(`组件 "${name}" 已注册，跳过重复注册: ${key}`);
			continue;
		}
		
		app.component(name, defineAsyncComponent(value as AsyncComponentLoader));
		registeredComponents.add(name);
		const pluginsName = key.match(/\/([^\/]*)\//)?.[1];
		pluginNames.add(pluginsName);
	}
	const dreamComponents = import.meta.glob('/node_modules/@great-dream/**/*.ts');
	// 遍历对象并注册异步组件
	for (let [key, value] of Object.entries(dreamComponents)) {
		key = key.replace('node_modules/@great-dream/', '');
		const name = key.slice(key.lastIndexOf('/') + 1, key.lastIndexOf('.'));
		
		// 避免重复注册同名组件
		if (registeredComponents.has(name)) {
			console.warn(`组件 "${name}" 已注册，跳过重复注册: ${key}`);
			continue;
		}
		
		app.component(name, defineAsyncComponent(value as AsyncComponentLoader));
		registeredComponents.add(name);
		const pluginsName = key.match(/\/([^\/]*)\//)?.[1];
		pluginNames.add(pluginsName);
	}
	pluginsAll = Array.from(pluginNames);
	console.log('已发现插件：', pluginsAll);
	for (const pluginName of pluginsAll) {
		const plugin = import(`./${pluginName}/index.ts`);
		plugin.then((module) => {
			app.use(module.default)
			console.log(`${pluginName}插件已加载`)
		}).catch((error) => {
			console.log(`${pluginName}插件下无index.ts`)
		})
	}
};
