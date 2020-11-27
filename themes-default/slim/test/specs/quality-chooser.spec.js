import Vuex, { Store } from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, shallowMount } from '@vue/test-utils';
import { QualityChooser } from '../../src/components';
import consts from '../../src/store/modules/config/consts';
import fixtures from '../__fixtures__/common';

describe('QualityChooser.test.js', () => {
    let localVue;
    let store;

    beforeEach(() => {
        localVue = createLocalVue();
        localVue.use(Vuex);
        localVue.use(VueRouter);

        const { state } = fixtures;
        store = new Store({
            modules: {
                consts: {
                    getters: consts.getters,
                    state: state.config.consts
                },
                config: {
                    state: state.config
                }
            }
        });
    });

    it('renders', async () => {
        const { state } = fixtures;
        const wrapper = shallowMount(QualityChooser, {
            localVue,
            store,
            sync: false,
            propsData: {
                overallQuality: undefined,
                keep: 'show'
            }
        });

        const isPreset = val => state.config.consts.qualities.presets.find(({ value }) => value === val) !== undefined;

        expect(wrapper.element).toMatchSnapshot('Base snapshot');

        // If `overallQuality` was not provided, `initialQuality` should be the default show quality
        expect(wrapper.vm.initialQuality).toBe(state.config.general.showDefaults.quality);
        // Custom quality elements should only be visible if the default quality is NOT a preset
        expect(wrapper.find('#customQualityWrapper').element).not.toBeVisible();
        expect(wrapper.find('#customQualityWrapper').element.style.display !== 'none').toBe(!isPreset(state.config.general.showDefaults.quality));

        // If `overallQuality` is provided, `initialQuality` should be that value
        wrapper.setProps({ overallQuality: 1000 }); // HD preset
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.initialQuality).toBe(1000);
        expect(wrapper.find('#customQualityWrapper').element).not.toBeVisible();

        // Choose a preset
        wrapper.setData({ selectedQualityPreset: 6 }); // SD preset
        await wrapper.vm.$nextTick();
        // Custom quality elements should be hidden
        expect(wrapper.find('#customQualityWrapper').element).not.toBeVisible();
        expect(wrapper.vm.allowedQualities).toEqual([2, 4]);
        expect(wrapper.vm.preferredQualities).toEqual([]);

        // Choose custom
        wrapper.setData({ selectedQualityPreset: 0 });
        await wrapper.vm.$nextTick();
        // Custom quality elements should now be visible
        expect(wrapper.find('#customQualityWrapper').element).toBeVisible();
        expect(wrapper.vm.allowedQualities).toEqual([2, 4]);
        expect(wrapper.vm.preferredQualities).toEqual([]);

        // Preferred qualities should be disabled if no allowed are selected
        wrapper.setData({
            selectedQualityPreset: 0,
            allowedQualities: []
        });
        await wrapper.vm.$nextTick();
        expect(wrapper.find('#customQualityWrapper').element).toBeVisible();
        expect(wrapper.findAll('#customQualityWrapper select').at(1).element).toBeDisabled();

        // Choose keep
        wrapper.setData({ selectedQualityPreset: 'keep' });
        await wrapper.vm.$nextTick();
        expect(wrapper.find('#customQualityWrapper').element).not.toBeVisible();
        // Underlying value should be equal to `initialQuality`
        expect(wrapper.vm.allowedQualities).toEqual([8, 32, 64, 128, 256, 512]); // HD preset
        expect(wrapper.vm.preferredQualities).toEqual([]);

        // And to custom again
        wrapper.setData({ selectedQualityPreset: 0 });
        await wrapper.vm.$nextTick();
        expect(wrapper.find('#customQualityWrapper').element).toBeVisible();
        // Underlying value should be equal to `initialQuality`
        expect(wrapper.vm.allowedQualities).toEqual([8, 32, 64, 128, 256, 512]); // HD preset
        expect(wrapper.vm.preferredQualities).toEqual([]);

        // Selecting qualities that sum up to a preset should not change the preset setting
        wrapper.setData({
            allowedQualities: [2, 4] // SD preset
        });
        await wrapper.vm.$nextTick();
        expect(wrapper.find('#customQualityWrapper').element).toBeVisible();
        expect(wrapper.vm.selectedQualityPreset).toEqual(0);

        // Deselecting all allowed qualities should clear the preferred selection
        wrapper.setData({
            allowedQualities: [2, 4],
            preferredQualities: [32]
        });
        wrapper.setData({ allowedQualities: [] });
        await wrapper.vm.$nextTick();
        expect(wrapper.findAll('#customQualityWrapper select').at(1).element).toBeDisabled();
        expect(wrapper.vm.allowedQualities).toEqual([]);
        expect(wrapper.vm.preferredQualities).toEqual([]);
    });
});
