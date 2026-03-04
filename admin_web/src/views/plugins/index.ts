import { defineAsyncComponent, AsyncComponentLoader } from 'vue';
export let pluginsAll: any = [];

// 扫描插件目录并注册插件
export const scanAndInstallPlugins = (app: any) => {
	// 只扫描 plugins 目录下的子目录中的组件文件（排除 index.ts 本身）
	const components = import.meta.glob('./*/**/*.ts', { eager: false });
	const pluginNames = new Set();
	const registeredComponents = new Set(); // 记录已注册的组件名，避免重复注册
	
	// 遍历对象并注册异步组件
	for (const [key, value] of Object.entries(components)) {
		const name = key.slice(key.lastIndexOf('/') + 1, key.lastIndexOf('.'));
		
		// 跳过 api.ts 和 index.ts 文件，这些不是组件
		if (name === 'api' || name === 'index') {
			continue;
		}
		
		// 避免重复注册同名组件
		if (registeredComponents.has(name)) {
			console.warn(`组件 "${name}" 已在其他插件中注册，跳过重复注册: ${key}`);
			continue;
		}
		
		// 注册组件
		app.component(name, defineAsyncComponent(value as AsyncComponentLoader));
		registeredComponents.add(name);
		
		// 提取插件名称（第一级子目录名）
		const pluginMatch = key.match(/^\.\/([^\/]+)\//);
		if (pluginMatch) {
			pluginNames.add(pluginMatch[1]);
		}
	}
	
	// 扫描 node_modules 中的 @great-dream 插件
	const dreamComponents = import.meta.glob('/node_modules/@great-dream/**/*.ts', { eager: false });
	for (let [key, value] of Object.entries(dreamComponents)) {
		key = key.replace('/node_modules/@great-dream/', '');
		const name = key.slice(key.lastIndexOf('/') + 1, key.lastIndexOf('.'));
		
		// 跳过 api.ts 和 index.ts 文件
		if (name === 'api' || name === 'index') {
			continue;
		}
		
		// 避免重复注册同名组件
		if (registeredComponents.has(name)) {
			console.warn(`组件 "${name}" 已注册，跳过 @great-dream 中的重复组件: ${key}`);
			continue;
		}
		
		// 注册组件
		app.component(name, defineAsyncComponent(value as AsyncComponentLoader));
		registeredComponents.add(name);
		
		// 提取插件名称
		const pluginMatch = key.match(/^([^\/]+)\//);
		if (pluginMatch) {
			pluginNames.add(pluginMatch[1]);
		}
	}
	
	pluginsAll = Array.from(pluginNames);
	
	if (pluginsAll.length > 0) {
		console.log('已发现插件：', pluginsAll);
		
		// 尝试加载每个插件的 index.ts 入口文件
		for (const pluginName of pluginsAll) {
			import(`./${pluginName}/index.ts`)
				.then((module) => {
					if (module.default) {
						app.use(module.default);
						console.log(`${pluginName} 插件已加载`);
					}
				})
				.catch(() => {
					// 插件没有 index.ts 入口文件，这是正常的
					// 只有组件文件的插件不需要 index.ts
				});
		}
	} else {
		console.log('未发现任何插件');
	}
};
