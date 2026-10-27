import Vuex, { Store } from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, mount } from '@vue/test-utils';
import $ from 'jquery';
import App from '../../src/components/app.vue';
import DisplayShow from '../../src/components/display-show.vue';
import ShowHeader from '../../src/components/show-header.vue';
import { addQTip, attachImdbTooltip } from '../../src/utils/jquery';
import showsModule from '../../src/store/modules/shows';
import fixtures from '../__fixtures__/common';
import showFixture from '../__fixtures__/show-detailed';

jest.mock('../../src/utils/jquery', () => ({ addQTip: jest.fn(), attachImdbTooltip: jest.fn() }));

describe('Show page lifecycle', () => {
    let localVue;
    let store;
    let wrappers;
    let windowListeners;
    let collapse;
    let previousCollapse;
    let qtip;
    let previousQtip;

    // Keep the real component lifecycle and methods, without rendering its unrelated controls.
    const showPage = methods => ({
        ...DisplayShow,
        render: h => h('div'),
        methods: { ...DisplayShow.methods, getCookie: () => null, loadShow: jest.fn(), ...methods }
    });
    const header = { ...ShowHeader, render: h => h('div') };
    const render = (component, options = {}) => {
        const wrapper = mount(component, { localVue, store, ...options });
        wrappers.push(wrapper);
        return wrapper;
    };
    const flush = async () => {
        await localVue.nextTick();
        await localVue.nextTick();
    };

    beforeEach(() => {
        localVue = createLocalVue();
        localVue.use(Vuex);
        localVue.use(VueRouter);
        const { state } = JSON.parse(JSON.stringify(fixtures));
        const show = { ...JSON.parse(JSON.stringify(showFixture)), seasons: [{ season: 1, children: [{ slug: 's01e01' }] }] };
        state.auth.isAuthenticated = true;
        store = new Store({
            state,
            mutations: {
                renameShow(state, title) {
                    state.shows.shows[0].title = title;
                }
            },
            modules: {
                shows: { ...showsModule, state: { shows: [show], currentShow: { showSlug: show.id.slug } } }
            }
        });
        wrappers = [];
        jest.useFakeTimers('modern');
        jest.spyOn(console, 'debug').mockImplementation(() => {});
        windowListeners = jest.spyOn(window, 'addEventListener');
        addQTip.mockClear();
        attachImdbTooltip.mockClear();
        previousCollapse = $.fn.collapse;
        collapse = jest.fn();
        $.fn.collapse = collapse;
        previousQtip = $.fn.qtip;
        qtip = jest.fn(function(command) {
            if (command === 'destroy') {
                this.removeAttr('data-hasqtip');
            }
        });
        $.fn.qtip = qtip;
    });

    afterEach(() => {
        wrappers.forEach(wrapper => wrapper.destroy());
        // Also clean up the leaking baseline, so each regression runs independently.
        windowListeners.mock.calls.filter(([event]) => ['load', 'resize'].includes(event))
            .forEach(([event, listener]) => window.removeEventListener(event, listener));
        $(document.body).off('click', '.seasonCheck');
        $('.seasonCheck').remove();
        $.fn.collapse = previousCollapse;
        $.fn.qtip = previousQtip;
        if (DisplayShow.methods.reflowLayout.cancel) {
            DisplayShow.methods.reflowLayout.cancel();
        }
        jest.clearAllTimers();
        jest.useRealTimers();
        jest.restoreAllMocks();
    });

    it('destroys query-keyed show pages while preserving Vuex episode rows for a revisit', async () => {
        const router = new VueRouter({
            routes: [
                { path: '/home', name: 'home', component: { render: h => h('div') } },
                { path: '/home/displayShow', name: 'show', component: showPage(), meta: { nocache: true } }
            ]
        });
        const cachedSeasons = store.state.shows.shows[0].seasons;
        await router.push('/home/displayShow?showslug=tvdb123');
        const wrapper = render(App, {
            router,
            stubs: ['load-progress-bar', 'app-header', 'sub-menu', 'vue-snotify', 'alerts', 'app-footer', 'scroll-buttons']
        });
        const firstPage = wrapper.findComponent({ name: 'show' }).vm;

        await router.push('/home/displayShow?showslug=tvdb456');
        await flush();
        const secondPage = wrapper.findComponent({ name: 'show' }).vm;
        await router.push('/home');
        await flush();

        expect(firstPage._isDestroyed).toBe(true);
        expect(secondPage._isDestroyed).toBe(true);
        await router.push('/home/displayShow?showslug=tvdb123');
        await flush();
        expect(wrapper.findComponent({ name: 'show' }).vm).not.toBe(firstPage);
        expect(store.state.shows.shows[0].seasons).toBe(cachedSeasons);
    });

    it('removes only the destroyed page\'s window and delegated season handlers', () => {
        const firstReflow = jest.fn();
        const secondReflow = jest.fn();
        const first = render(showPage({ reflowLayout: firstReflow }));
        render(showPage({ reflowLayout: secondReflow }));
        first.destroy();
        window.dispatchEvent(new Event('resize'));
        const checkbox = $('<input class="seasonCheck" id="1" type="checkbox">').appendTo(document.body);
        checkbox.trigger('click');
        jest.runOnlyPendingTimers();

        expect(firstReflow).not.toHaveBeenCalled();
        expect(secondReflow).toHaveBeenCalledTimes(1);
        expect(collapse).toHaveBeenCalledTimes(1);
        expect(collapse).toHaveBeenCalledWith('show');
    });

    it('cancels a destroyed page\'s queued reflow without cancelling a live sibling', () => {
        const first = render(showPage());
        const second = render(showPage());
        first.vm.reflowLayout();
        second.vm.reflowLayout();
        second.destroy();
        jest.runOnlyPendingTimers();

        expect(addQTip).toHaveBeenCalledTimes(1);
        addQTip.mockClear();
        first.vm.reflowLayout();
        first.destroy();
        jest.runOnlyPendingTimers();
        expect(addQTip).not.toHaveBeenCalled();
    });

    it('destroys subtitle searches manually mounted by the page', () => {
        const wrapper = render(showPage());
        const subtitleSearch = render({ render: h => h('div') });
        wrapper.vm.subtitleSearchComponents.push(subtitleSearch.vm);
        wrapper.destroy();

        expect(subtitleSearch.vm._isDestroyed).toBe(true);
    });

    it('ignores show details that finish loading after the page was destroyed', async () => {
        let resolveDetails;
        const getShow = jest.fn(() => new Promise(resolve => {
            resolveDetails = resolve;
        }));
        const setCurrentShow = jest.fn();
        const initializeEpisodes = jest.fn();
        const wrapper = render(showPage({
            loadShow: DisplayShow.methods.loadShow, getShow, setCurrentShow, initializeEpisodes
        }), { propsData: { slug: store.state.shows.shows[0].id.slug } });
        wrapper.destroy();
        resolveDetails({ fileCacheRevision: 0 });
        await flush();

        expect(setCurrentShow).not.toHaveBeenCalled();
        expect(initializeEpisodes).not.toHaveBeenCalled();
    });

    it('does not initialize episodes when a pending cache refresh finishes after destruction', async () => {
        let resolveRefresh;
        const refreshShowFiles = jest.fn(() => new Promise(resolve => {
            resolveRefresh = resolve;
        }));
        const initializeEpisodes = jest.fn();
        const wrapper = render(showPage({
            loadShow: DisplayShow.methods.loadShow,
            getShow: jest.fn().mockResolvedValue({ fileCacheRevision: 0 }),
            setCurrentShow: jest.fn(),
            refreshShowFiles,
            initializeEpisodes
        }), { propsData: { slug: store.state.shows.shows[0].id.slug } });
        store.commit('invalidateShowEpisodeCache', { showSlug: store.state.shows.shows[0].id.slug });
        await flush();
        expect(refreshShowFiles).toHaveBeenCalledTimes(1);
        wrapper.destroy();
        resolveRefresh();
        await flush();

        expect(initializeEpisodes).not.toHaveBeenCalled();
    });

    it('stops sequential episode requests when the page is destroyed between seasons', async () => {
        let resolveEpisodes;
        const getEpisodes = jest.fn(() => new Promise(resolve => {
            resolveEpisodes = resolve;
        }));
        const wrapper = render(showPage({ getEpisodes, neededSeasons: () => [1, 2] }), {
            propsData: { slug: store.state.shows.shows[0].id.slug }
        });
        wrapper.vm.loadEpisodes(1, true);
        expect(getEpisodes).toHaveBeenCalledTimes(1);
        wrapper.destroy();
        resolveEpisodes();
        await flush();

        expect(getEpisodes).toHaveBeenCalledTimes(1);
    });

    it.each(['show page', 'show header'])('destroys only the departing %s\'s tooltips', async component => {
        const wrapper = render({
            ...(component === 'show page' ? showPage() : header),
            render: h => h('div', [h('span', { attrs: { 'data-hasqtip': 'departing' } })])
        }, { propsData: { slug: store.state.shows.shows[0].id.slug } });
        const sibling = render({ render: h => h('span', { attrs: { 'data-hasqtip': 'live' } }) });
        const target = wrapper.find('[data-hasqtip]').element;
        await flush();
        wrapper.destroy();

        expect(qtip).toHaveBeenCalledTimes(1);
        expect(qtip).toHaveBeenCalledWith('destroy', true);
        expect(target.hasAttribute('data-hasqtip')).toBe(false);
        expect(sibling.attributes('data-hasqtip')).toBe('live');
    });

    it('destroys a cached header\'s tooltips when deactivated', async () => {
        const { slug } = store.state.shows.shows[0].id;
        const headerWithTooltip = {
            ...header,
            render: h => h('div', [h('span', { attrs: { 'data-hasqtip': 'hidden' } })])
        };
        const wrapper = render({
            data: () => ({ visible: true }),
            render(h) {
                return h('keep-alive', [this.visible ? h(headerWithTooltip, { props: { slug } }) : h('div')]);
            }
        });
        const target = wrapper.find('[data-hasqtip]').element;
        await wrapper.setData({ visible: false });

        expect(qtip).toHaveBeenCalledWith('destroy', true);
        expect(target.hasAttribute('data-hasqtip')).toBe(false);
    });

    it('removes a destroyed header\'s listeners without disabling a live sibling', async () => {
        const { slug } = store.state.shows.shows[0].id;
        const first = render(header, { propsData: { slug } });
        render(header, { propsData: { slug } });
        await flush();
        attachImdbTooltip.mockClear();
        first.destroy();
        window.dispatchEvent(new Event('resize'));
        await flush();

        expect(attachImdbTooltip).toHaveBeenCalledTimes(1);
    });

    it('does not run a header layout callback queued before destruction', async () => {
        const wrapper = render(header, { propsData: { slug: store.state.shows.shows[0].id.slug } });
        await flush();
        attachImdbTooltip.mockClear();
        window.dispatchEvent(new Event('resize'));
        wrapper.destroy();
        await flush();

        expect(attachImdbTooltip).not.toHaveBeenCalled();
    });

    it('reflows once on initial activation and when an unchanged cached header returns', async () => {
        const { slug } = store.state.shows.shows[0].id;
        const wrapper = render({
            data: () => ({ visible: true }),
            render(h) {
                return h('keep-alive', [this.visible ? h(header, { props: { slug } }) : h('div')]);
            }
        });
        await flush();
        expect(attachImdbTooltip).toHaveBeenCalledTimes(1);
        attachImdbTooltip.mockClear();

        await wrapper.setData({ visible: false });
        await flush();
        expect(attachImdbTooltip).not.toHaveBeenCalled();
        await wrapper.setData({ visible: true });
        await flush();

        expect(attachImdbTooltip).toHaveBeenCalledTimes(1);
    });

    it('suspends a cached header\'s listeners and show watcher, then restores them once', async () => {
        const { slug } = store.state.shows.shows[0].id;
        const wrapper = render({
            data: () => ({ visible: true }),
            render(h) {
                return h('keep-alive', [this.visible ? h(header, { props: { slug } }) : h('div')]);
            }
        });
        await wrapper.setData({ visible: false });
        attachImdbTooltip.mockClear();
        window.dispatchEvent(new Event('resize'));
        store.commit('renameShow', 'Changed while inactive');
        await flush();
        expect(attachImdbTooltip).not.toHaveBeenCalled();

        await wrapper.setData({ visible: true });
        await flush();
        attachImdbTooltip.mockClear();
        window.dispatchEvent(new Event('resize'));
        await flush();
        expect(attachImdbTooltip).toHaveBeenCalledTimes(1);
        attachImdbTooltip.mockClear();
        store.commit('renameShow', 'Changed while active');
        await flush();
        expect(attachImdbTooltip).toHaveBeenCalledTimes(1);
    });
});
