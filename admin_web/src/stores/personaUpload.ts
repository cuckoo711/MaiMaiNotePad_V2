import { defineStore } from 'pinia';
import { Local } from '/@/utils/storage';

/**
 * 人设卡上传状态管理
 * 
 * 功能：
 * - 管理上传向导的当前步骤
 * - 保存和恢复草稿数据到 localStorage
 * - 管理基本信息、配置数据和敏感信息检测状态
 * 
 * 验证需求：7.6, 7.7, 14.9
 */

// 基本信息接口
export interface BasicInfo {
	name: string;              // 人设卡名称（1-200 字符）
	description: string;       // 人设卡描述（至少 10 字符）
	copyright_owner?: string;  // 版权所有者（可选，默认为上传者用户名）
	tags?: string;             // 标签（可选，多个标签用逗号分隔）
	is_public: boolean;        // 是否公开（默认为 false）
}

// 配置项接口
export interface ConfigItem {
	key: string;               // 配置键名
	value: any;                // 配置值
	type: 'string' | 'integer' | 'float' | 'boolean' | 'array' | 'object'; // 数据类型
	comment?: string;          // 注释
	is_deleted?: boolean;      // 是否删除
}

// 配置块接口
export interface ConfigSection {
	name: string;              // 配置块名称
	comment?: string;          // 块注释
	items: ConfigItem[];       // 配置项列表
	is_deleted?: boolean;      // 是否删除整个块
}

// 解析后的配置接口
export interface ParsedConfig {
	sections: ConfigSection[]; // 配置块列表
	version: string;           // 配置版本
	file_name?: string;        // 原始文件名
	file_size?: number;        // 文件大小
}

// 敏感信息项接口
export interface SensitiveItem {
	section: string;           // 配置块名称
	key: string;               // 配置键名
	value: string;             // 包含敏感信息的值
	matches: string[];         // 匹配到的敏感信息列表（5-11 位数字）
	path: string;              // 配置项路径（section.key）
}

// 敏感信息确认数据接口
export interface SensitiveConfirmation {
	confirmation_text: string; // 确认声明文本
	sensitive_locations: SensitiveItem[]; // 敏感信息位置列表
	captcha_key?: string;      // 验证码 key
	captcha_value?: string;    // 验证码答案
}

// Store 状态接口
export interface PersonaUploadState {
	currentStep: number;                    // 当前步骤（1: 基本信息, 2: 配置编辑）
	basicInfo: BasicInfo;                   // 基本信息
	parsedConfig: ParsedConfig | null;      // 解析后的配置
	sensitiveItems: SensitiveItem[];        // 检测到的敏感信息列表
	hasSensitiveInfo: boolean;              // 是否包含敏感信息
	draftKey: string;                       // localStorage 草稿键名
	isDraftLoaded: boolean;                 // 是否已加载草稿
}

/**
 * 人设卡上传 Store
 */
export const usePersonaUploadStore = defineStore('personaUpload', {
	state: (): PersonaUploadState => ({
		currentStep: 1,
		basicInfo: {
			name: '',
			description: '',
			copyright_owner: '',
			tags: '',
			is_public: false,
		},
		parsedConfig: null,
		sensitiveItems: [],
		hasSensitiveInfo: false,
		draftKey: 'persona_upload_draft',
		isDraftLoaded: false,
	}),

	getters: {
		/**
		 * 获取当前步骤
		 */
		getCurrentStep(): number {
			return this.currentStep;
		},

		/**
		 * 检查基本信息是否有效
		 */
		isBasicInfoValid(): boolean {
			const { name, description } = this.basicInfo;
			return name.length >= 1 && name.length <= 200 && description.length >= 10;
		},

		/**
		 * 检查是否有配置数据
		 */
		hasConfigData(): boolean {
			return this.parsedConfig !== null && this.parsedConfig.sections.length > 0;
		},

		/**
		 * 获取被删除的配置块列表
		 */
		getDeletedSections(): string[] {
			if (!this.parsedConfig) return [];
			return this.parsedConfig.sections
				.filter(section => section.is_deleted)
				.map(section => section.name);
		},

		/**
		 * 检查是否可以提交
		 */
		canSubmit(): boolean {
			return this.isBasicInfoValid && this.hasConfigData;
		},
	},

	actions: {
		/**
		 * 设置当前步骤
		 * @param step 步骤编号（1 或 2）
		 */
		setCurrentStep(step: number) {
			if (step >= 1 && step <= 2) {
				this.currentStep = step;
				this.saveDraft();
			}
		},

		/**
		 * 前进到下一步
		 */
		nextStep() {
			if (this.currentStep < 2) {
				this.currentStep++;
				this.saveDraft();
			}
		},

		/**
		 * 返回上一步
		 */
		prevStep() {
			if (this.currentStep > 1) {
				this.currentStep--;
				this.saveDraft();
			}
		},

		/**
		 * 更新基本信息
		 * @param info 基本信息对象
		 */
		updateBasicInfo(info: Partial<BasicInfo>) {
			this.basicInfo = { ...this.basicInfo, ...info };
			this.saveDraft();
		},

		/**
		 * 设置解析后的配置
		 * @param config 解析后的配置对象
		 */
		setParsedConfig(config: ParsedConfig) {
			this.parsedConfig = config;
			this.saveDraft();
		},

		/**
		 * 更新配置项
		 * @param sectionName 配置块名称
		 * @param itemKey 配置项键名
		 * @param updates 更新的字段
		 */
		updateConfigItem(sectionName: string, itemKey: string, updates: Partial<ConfigItem>) {
			if (!this.parsedConfig) return;

			const section = this.parsedConfig.sections.find(s => s.name === sectionName);
			if (!section) return;

			const item = section.items.find(i => i.key === itemKey);
			if (!item) return;

			Object.assign(item, updates);
			this.saveDraft();
		},

		/**
		 * 更新配置块
		 * @param sectionName 配置块名称
		 * @param updates 更新的字段
		 */
		updateConfigSection(sectionName: string, updates: Partial<ConfigSection>) {
			if (!this.parsedConfig) return;

			const section = this.parsedConfig.sections.find(s => s.name === sectionName);
			if (!section) return;

			Object.assign(section, updates);
			this.saveDraft();
		},

		/**
		 * 标记配置块为已删除
		 * @param sectionName 配置块名称
		 * @param isDeleted 是否删除
		 */
		markSectionDeleted(sectionName: string, isDeleted: boolean) {
			if (!this.parsedConfig) return;

			const section = this.parsedConfig.sections.find(s => s.name === sectionName);
			if (!section) return;

			section.is_deleted = isDeleted;
			// 同时标记该块下所有配置项为已删除
			section.items.forEach(item => {
				item.is_deleted = isDeleted;
			});
			this.saveDraft();
		},

		/**
		 * 设置敏感信息列表
		 * @param items 敏感信息项列表
		 */
		setSensitiveItems(items: SensitiveItem[]) {
			this.sensitiveItems = items;
			this.hasSensitiveInfo = items.length > 0;
			this.saveDraft();
		},

		/**
		 * 清除敏感信息
		 */
		clearSensitiveItems() {
			this.sensitiveItems = [];
			this.hasSensitiveInfo = false;
			this.saveDraft();
		},

		/**
		 * 保存草稿到 localStorage
		 * 
		 * 验证需求：7.6
		 */
		saveDraft() {
			try {
				const draft = {
					currentStep: this.currentStep,
					basicInfo: this.basicInfo,
					parsedConfig: this.parsedConfig,
					sensitiveItems: this.sensitiveItems,
					hasSensitiveInfo: this.hasSensitiveInfo,
					timestamp: Date.now(), // 保存时间戳
				};
				Local.set(this.draftKey, draft);
			} catch (error) {
				console.error('保存草稿失败:', error);
			}
		},

		/**
		 * 从 localStorage 恢复草稿
		 * 
		 * 验证需求：7.7
		 * 
		 * @returns 是否成功恢复草稿
		 */
		loadDraft(): boolean {
			try {
				const draft = Local.get(this.draftKey);
				if (!draft) {
					this.isDraftLoaded = false;
					return false;
				}

				// 检查草稿是否过期（24 小时）
				const now = Date.now();
				const draftAge = now - (draft.timestamp || 0);
				const maxAge = 24 * 60 * 60 * 1000; // 24 小时

				if (draftAge > maxAge) {
					// 草稿过期，清除
					this.clearDraft();
					this.isDraftLoaded = false;
					return false;
				}

				// 恢复草稿数据
				this.currentStep = draft.currentStep || 1;
				this.basicInfo = draft.basicInfo || {
					name: '',
					description: '',
					copyright_owner: '',
					tags: '',
					is_public: false,
				};
				this.parsedConfig = draft.parsedConfig || null;
				this.sensitiveItems = draft.sensitiveItems || [];
				this.hasSensitiveInfo = draft.hasSensitiveInfo || false;
				this.isDraftLoaded = true;

				return true;
			} catch (error) {
				console.error('恢复草稿失败:', error);
				this.isDraftLoaded = false;
				return false;
			}
		},

		/**
		 * 清除草稿
		 */
		clearDraft() {
			try {
				Local.remove(this.draftKey);
			} catch (error) {
				console.error('清除草稿失败:', error);
			}
		},

		/**
		 * 重置所有状态
		 */
		reset() {
			this.currentStep = 1;
			this.basicInfo = {
				name: '',
				description: '',
				copyright_owner: '',
				tags: '',
				is_public: false,
			};
			this.parsedConfig = null;
			this.sensitiveItems = [];
			this.hasSensitiveInfo = false;
			this.isDraftLoaded = false;
			this.clearDraft();
		},

		/**
		 * 生成提交数据
		 * 
		 * @returns 提交给后端的数据对象
		 */
		generateSubmitData() {
			if (!this.canSubmit) {
				throw new Error('数据不完整，无法提交');
			}

			return {
				// 基本信息
				name: this.basicInfo.name,
				description: this.basicInfo.description,
				copyright_owner: this.basicInfo.copyright_owner || undefined,
				tags: this.basicInfo.tags || undefined,
				is_public: this.basicInfo.is_public,
				// 配置数据
				configs: this.parsedConfig!.sections,
				// 版本信息
				version: this.parsedConfig!.version,
			};
		},

		/**
		 * 生成敏感信息确认数据
		 * 
		 * @param captchaKey 验证码 key
		 * @param captchaValue 验证码答案
		 * @returns 敏感信息确认数据对象
		 */
		generateSensitiveConfirmation(captchaKey: string, captchaValue: string): SensitiveConfirmation {
			if (!this.hasSensitiveInfo) {
				throw new Error('没有检测到敏感信息');
			}

			// 生成确认声明文本
			const locations = this.sensitiveItems.map(item => item.path).join('、');
			const confirmationText = `我已确认该文件在 ${locations} 的内容不涉及个人隐私信息`;

			return {
				confirmation_text: confirmationText,
				sensitive_locations: this.sensitiveItems,
				captcha_key: captchaKey,
				captcha_value: captchaValue,
			};
		},
	},
});
