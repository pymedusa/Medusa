import Vuex, { Store } from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, shallowMount } from '@vue/test-utils';
import { ConfigGeneral } from '../../src/components';
import consts from '../../src/store/modules/config/consts';
import fixtures from '../__fixtures__/common';

describe('ConfigGeneral.test.js', () => {
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

    it('renders', () => {
        // Prevents `TypeError: $(...).tabs is not a function`
        ConfigGeneral.beforeMount = () => {};

        const wrapper = shallowMount(ConfigGeneral, {
            localVue,
            store,
            stubs: [
                'app-link',
                'file-browser',
                'name-pattern',
                'select-list',
                'toggle-button'
            ],
            computed: {
                timePresetOptions() {
                    return [
                        { value: '%I:%M:%S %p', text: '03:32:16 PM' },
                        { value: '%H:%M:%S', text: '15:32:16' }
                    ];
                },
                datePresetOptions() {
                    return [
                        { value: '%x', text: 'Use System Default' },
                        { value: '%Y-%m-%d', text: '2019-11-21' },
                        { value: '%a, %Y-%m-%d', text: 'Thu, 2019-11-21' },
                        { value: '%A, %Y-%m-%d', text: 'Thursday, 2019-11-21' },
                        { value: '%y-%m-%d', text: '19-11-21' },
                        { value: '%a, %y-%m-%d', text: 'Thu, 19-11-21' },
                        { value: '%A, %y-%m-%d', text: 'Thursday, 19-11-21' },
                        { value: '%m/%d/%Y', text: '11/21/2019' },
                        { value: '%a, %m/%d/%Y', text: 'Thu, 11/21/2019' }
                    ];
                }
            }
        });

        expect(wrapper.element).toMatchSnapshot();
    });
});
