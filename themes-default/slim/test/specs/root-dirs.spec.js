import Vuex, { Store } from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, mount } from '@vue/test-utils';
import { RootDirs } from '../../src/components';
import fixtures from '../__fixtures__/root-dirs';

describe('RootDirs.test.js', () => {
    let localVue;
    let store;

    beforeEach(() => {
        localVue = createLocalVue();
        localVue.use(Vuex);
        localVue.use(VueRouter);

        const { state } = fixtures;
        store = new Store({ state });
    });

    test('renders and changing default/selected', () => {
        const { state } = fixtures;
        const wrapper = mount(RootDirs, {
            localVue,
            store
        });

        const rawRootDirs = state.config.general.rootDirs;
        const defaultIndex = rawRootDirs[0];
        const rawPaths = rawRootDirs.slice(1);
        const { vm } = wrapper;

        expect(wrapper.element).toMatchSnapshot('Base snapshot');

        // Make sure all the paths are rendered
        expect(vm.rootDirs).toEqual(vm.transformRaw(rawRootDirs));

        const select = wrapper.find('select');
        expect(select.isEmpty()).toBe(false);

        const selectOptions = select.findAll('option');
        expect(selectOptions.length).toEqual(rawPaths.length);

        // Make sure the default root dir is marked
        const defaultRootDir = rawPaths[defaultIndex];
        expect(vm.defaultRootDir).toEqual(defaultRootDir);
        expect(selectOptions.at(defaultIndex).text()).toEqual(`* ${defaultRootDir}`);
        expect(selectOptions.at(defaultIndex).element.value).toEqual('/media/Anime/');

        // Test changing default root dir
        const newDefault = rawPaths.find((_path, index) => index !== defaultIndex);
        wrapper.setData({ defaultRootDir: newDefault });
        expect(vm.defaultRootDir).toEqual(newDefault);
        expect(wrapper.element).toMatchSnapshot('After changing the default root dir');

        // Test changing selected root dir
        const newSelectionIndex = rawPaths.findIndex((_path, index) => index !== vm.selectedRootDir);
        const newSelection = rawPaths[newSelectionIndex];
        wrapper.setData({ selectedRootDir: newSelection });
        expect(vm.selectedRootDir).toEqual(newSelection);
        expect(selectOptions.at(newSelectionIndex).element.value).toEqual('/media/TV');
    });
});
