import test from 'ava';
import Vuex from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, mount } from '@vue/test-utils';
import { RootDirs } from '../../static/js/templates';
import fixtures from '../__fixtures__/root-dirs';

test.beforeEach(t => {
    t.context.localVue = createLocalVue();
    t.context.localVue.use(Vuex);
    t.context.localVue.use(VueRouter);

    const { state } = fixtures;
    const { Store } = Vuex;
    t.context.state = state;
    t.context.store = new Store({ state });
});

test('renders and changing default/selected', t => {
    const { localVue, store, state } = t.context;
    const wrapper = mount(RootDirs, {
        localVue,
        store
    });

    const rawRootDirs = state.config.rootDirs;
    const defaultIndex = rawRootDirs[0];
    const rawPaths = rawRootDirs.slice(1);
    const { vm } = wrapper;

    t.snapshot(wrapper.html(), 'Base snapshot');

    // Make sure all the paths are rendered
    t.deepEqual(vm.rootDirs, vm.transformRaw(rawRootDirs));
    const select = wrapper.find('select');
    t.false(select.isEmpty());
    const selectOptions = select.findAll('option');
    t.is(selectOptions.length, rawPaths.length);

    // Make sure the default root dir is marked
    const defaultRootDir = rawPaths[defaultIndex];
    t.is(vm.defaultRootDir, defaultRootDir);
    t.is(selectOptions.at(defaultIndex).text(), `* ${defaultRootDir}`);
    t.true(selectOptions.at(defaultIndex).is(':selected'));

    // Test changing default root dir
    const newDefault = rawPaths.find((_path, index) => index !== defaultIndex);
    wrapper.setData({ defaultRootDir: newDefault });
    t.is(vm.defaultRootDir, newDefault);
    t.snapshot(wrapper.html(), 'After changing the default root dir');

    // Test changing selected root dir
    const newSelectionIndex = rawPaths.findIndex((_path, index) => index !== vm.selectedRootDir);
    const newSelection = rawPaths[newSelectionIndex];
    wrapper.setData({ selectedRootDir: newSelection });
    t.is(vm.selectedRootDir, newSelection);
    t.true(selectOptions.at(newSelectionIndex).is(':selected'));
});
