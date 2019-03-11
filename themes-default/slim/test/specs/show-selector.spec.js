import Vuex from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, mount } from '@vue/test-utils';
import { ShowSelector } from '../../src/components';
import fixtures from '../__fixtures__/common';
import { shows } from '../__fixtures__/shows';

describe('ShowSelector.test.js', () => {
    let localVue;
    let store;

    beforeEach(() => {
        localVue = createLocalVue();
        localVue.use(Vuex);
        localVue.use(VueRouter);

        const { state } = fixtures;
        const { Store } = Vuex;
        store = new Store({ state });
    });

    it('renders "loading..." with empty show array', () => {
        const wrapper = mount(ShowSelector, {
            localVue,
            computed: {
                shows() {
                    return [];
                },
                config() {
                    return {
                        animeSplitHome: false,
                        sortArticle: 'asc'
                    };
                }
            },
            store
        });

        expect(wrapper.element).toMatchSnapshot();
    });

    it('renders with shows', () => {
        const wrapper = mount(ShowSelector, {
            localVue,
            computed: {
                shows() {
                    return shows;
                },
                config() {
                    return {
                        animeSplitHome: false,
                        sortArticle: true
                    };
                }
            },
            propsData: {
                placeholder: '-- Select a Show --'
            },
            store
        });

        expect(wrapper.element).toMatchSnapshot();
    });

    it('renders with articles(The|A|An) ignored', () => {
        const wrapper = mount(ShowSelector, {
            localVue,
            computed: {
                shows() {
                    return shows;
                },
                config() {
                    return {
                        animeSplitHome: false,
                        sortArticle: false
                    };
                }
            },
            propsData: {
                placeholder: '-- Select a Show --'
            },
            store
        });

        expect(wrapper.element).toMatchSnapshot();
    });

    it('renders with split sections', () => {
        const wrapper = mount(ShowSelector, {
            localVue,
            computed: {
                shows() {
                    return shows;
                },
                config() {
                    return {
                        animeSplitHome: false,
                        sortArticle: 'asc'
                    };
                }
            },
            propsData: {
                placeholder: '-- Select a Show --'
            },
            store
        });

        expect(wrapper.element).toMatchSnapshot();
    });

    it('renders without placeholder', () => {
        const wrapper = mount(ShowSelector, {
            localVue,
            computed: {
                shows() {
                    return shows;
                },
                config() {
                    return {
                        animeSplitHome: false,
                        sortArticle: 'asc'
                    };
                }
            },
            store
        });

        expect(wrapper.element).toMatchSnapshot();
    });
});
