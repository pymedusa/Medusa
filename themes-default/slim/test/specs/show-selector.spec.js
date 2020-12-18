import Vuex, { Store } from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, shallowMount } from '@vue/test-utils';
import { ShowSelector } from '../../src/components';
import fixtures from '../__fixtures__/common';
import { shows } from '../__fixtures__/shows';
import showLists from '../__fixtures__/show-lists';

describe('ShowSelector.test.js', () => {
    let localVue;
    let store;
    let router;

    beforeEach(() => {
        localVue = createLocalVue();
        localVue.use(Vuex);
        localVue.use(VueRouter);

        const { state } = fixtures;
        store = new Store({ state });
        const routes = [
            {
                path: '/home/displayShow',
                name: 'show',
                component: () => import('../../src/components/display-show.vue')
            },
            {
                path: '/home/editShow',
                name: 'editShow',
                component: () => import('../../src/components/edit-show.vue')
            }
        ];

        router = new VueRouter({
            routes
        });

        // Let's start navigating to displayShow, which should also display the show-selector.
        router.push({ name: 'show', query: { indexername: 'tvdb', seriesid: String(12345) } });
    });

    it('renders "loading..." with empty show array in /home/displayShow', () => {
        const wrapper = shallowMount(ShowSelector, {
            localVue,
            computed: {
                showsInLists() {
                    return [];
                },
                shows() {
                    return [];
                },
                layout() {
                    return {
                        sortArticle: true
                    };
                }
            },
            store,
            router
        });

        expect(wrapper.element).toMatchSnapshot();
    });

    it('renders with shows in /home/displayShow', () => {
        const wrapper = shallowMount(ShowSelector, {
            localVue,
            computed: {
                showsInLists() {
                    return showLists;
                },
                shows() {
                    return shows;
                },
                layout() {
                    return {
                        sortArticle: true
                    };
                }
            },
            propsData: {
                placeholder: '-- Select a Show --'
            },
            store,
            router
        });

        expect(wrapper.element).toMatchSnapshot();
    });

    it('renders with articles(The|A|An) ignored in /home/displayShow', () => {
        const wrapper = shallowMount(ShowSelector, {
            localVue,
            computed: {
                showsInLists() {
                    return showLists;
                },
                shows() {
                    return shows;
                },
                layout() {
                    return {
                        sortArticle: false
                    };
                }
            },
            propsData: {
                placeholder: '-- Select a Show --'
            },
            store,
            router
        });

        expect(wrapper.element).toMatchSnapshot();
    });

    it('renders with split sections in /home/displayShow', () => {
        const wrapper = shallowMount(ShowSelector, {
            localVue,
            computed: {
                showsInLists() {
                    return showLists;
                },
                shows() {
                    return shows;
                },
                layout() {
                    return {
                        sortArticle: true
                    };
                }
            },
            propsData: {
                placeholder: '-- Select a Show --'
            },
            store,
            router
        });

        expect(wrapper.element).toMatchSnapshot();
    });

    it('renders without placeholder in /home/displayShow', () => {
        const wrapper = shallowMount(ShowSelector, {
            localVue,
            computed: {
                showsInLists() {
                    return showLists;
                },
                shows() {
                    return shows;
                },
                layout() {
                    return {
                        sortArticle: true
                    };
                }
            },
            store,
            router
        });

        expect(wrapper.element).toMatchSnapshot();
    });

    it('renders with shows in /home/editShow', () => {
        // Navigate to editShow, which should also display the show-selector.
        router.push({ name: 'editShow', query: { indexername: 'tvdb', seriesid: String(12345) } });
        const wrapper = shallowMount(ShowSelector, {
            localVue,
            computed: {
                showsInLists() {
                    return showLists;
                },
                shows() {
                    return shows;
                },
                layout() {
                    return {
                        sortArticle: true
                    };
                }
            },
            propsData: {
                placeholder: '-- Select a Show --'
            },
            store,
            router
        });

        expect(wrapper.element).toMatchSnapshot();
    });
});
