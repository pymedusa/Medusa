import Vuex, { Store } from 'vuex';
import { createLocalVue, shallowMount } from '@vue/test-utils';
import { AppHeader } from '../../src/components';
import fixtures from '../__fixtures__/common';

describe('AppHeader.test.js', () => {
    let localVue;
    let store;

    beforeEach(() => {
        localVue = createLocalVue();
        localVue.use(Vuex);

        const { state } = fixtures;
        store = new Store({ state });
    });

    it('renders', () => {
        const wrapper = shallowMount(AppHeader, {
            localVue,
            store,
            computed: {
                topMenu() {
                    return 'home';
                },
                currentShowRoute() {
                    return {
                        name: 'show',
                        query: {
                            indexername: 'tvdb',
                            seriesid: 253463
                        }
                    };
                }
            }
        });

        expect(wrapper.element).toMatchSnapshot();
    });
});
