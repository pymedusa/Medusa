import Vue from 'vue';
import Vuex from 'vuex';
import { createLocalVue, shallowMount } from '@vue/test-utils';
import History from '../../src/components/history.vue';
import HistoryDetailed from '../../src/components/history-detailed.vue';
import HistoryCompact from '../../src/components/history-compact.vue';
import historyModule from '../../src/store/modules/history';
import { normalizeHistorySizeFilter, normalizeHistoryTextFilter } from '../../src/utils/history';

Vue.use(Vuex);

const VueGoodTableStub = {
    props: ['columns', 'rows', 'totalRows', 'searchOptions', 'sortOptions', 'paginationOptions', 'columnFilterOptions', 'rowStyleClass', 'styleClass'],
    data() {
        return {
            headerSort: []
        };
    },
    watch: {
        sortOptions: {
            deep: true,
            handler(nextOptions, previousOptions) {
                const nextSort = JSON.stringify(nextOptions && nextOptions.initialSortBy);
                const previousSort = JSON.stringify(previousOptions && previousOptions.initialSortBy);
                if (nextSort !== previousSort) {
                    this.initializeSort();
                }
            }
        }
    },
    methods: {
        emitSort(sort) {
            this.headerSort = sort.map(item => Object.assign({}, item));
            this.$emit('on-sort-change', this.headerSort);
        },
        initializeSort() {
            this.emitSort(this.sortOptions.initialSortBy.map(sort => Object.assign({}, sort)));
        }
    },
    render(h) {
        const slot = this.$scopedSlots['column-filter'];
        const fields = ['episodeTitle', 'providerId', 'size'];
        return h('div', fields.map(field => slot ? slot({
            column: {
                field
            }
        }) : null));
    }
};

const VueGoodTableInitialPageStub = {
    props: VueGoodTableStub.props,
    created() {
        this.$emit('on-page-change', {
            currentPage: 1
        });
    },
    render(h) {
        return h('div');
    }
};

const consts = {
    qualities: {
        values: [{
            value: '1',
            text: 'test'
        }]
    },
    clientStatuses: [{
        value: 0,
        name: 'Snatched'
    }, {
        value: 1,
        name: 'Paused'
    }, {
        value: 2,
        name: 'Downloading'
    }, {
        value: 4,
        name: 'Downloaded'
    }, {
        value: 8,
        name: 'Seeded'
    }, {
        value: 16,
        name: 'Failed'
    }, {
        value: 32,
        name: 'Aborted'
    }, {
        value: 64,
        name: 'Extracting'
    }, {
        value: 128,
        name: 'Completed'
    }, {
        value: 256,
        name: 'Postprocessed'
    }, {
        value: 512,
        name: 'SeededAction'
    }, {
        value: 1024,
        name: 'Removed'
    }]
};

const clientStatusOption = value => consts.clientStatuses.find(option => option.value === value);

const createLocalVueForHistory = () => {
    const localVue = createLocalVue();
    localVue.use(Vuex);
    return localVue;
};

const cloneHistoryState = () => JSON.parse(JSON.stringify(historyModule.state));

const createHistoryStore = (history = {}) => {
    const {
        remote = {},
        remoteCompact = {},
        layout = 'detailed',
        ...historyState
    } = history;
    const moduleState = cloneHistoryState();
    moduleState.remote = {
        ...moduleState.remote,
        ...remote
    };
    moduleState.remoteCompact = {
        ...moduleState.remoteCompact,
        ...remoteCompact
    };
    Object.assign(moduleState, historyState);

    return new Vuex.Store({
        modules: {
            auth: {
                state: {
                    client: {
                        api: {
                            get: jest.fn(() => Promise.resolve({
                                data: [],
                                headers: {
                                    'x-pagination-count': '0'
                                }
                            }))
                        }
                    }
                }
            },
            config: {
                state: {
                    consts,
                    general: {
                        randomShowSlug: ''
                    },
                    layout: {
                        history: layout
                    }
                }
            },
            history: {
                ...historyModule,
                state: moduleState
            }
        },
        getters: {
            fuzzyParseDateTime: () => () => ''
        },
        actions: {
            setLayout({ rootState }, { page, layout }) {
                rootState.config.layout[page] = layout;
            },
            checkHistory: jest.fn(),
            setStoreLayout: jest.fn()
        }
    });
};

const makeMountedHistoryComponent = (component, cookieStore = {}) => {
    const getCookie = jest.fn(key => {
        return cookieStore[key];
    });
    const setCookie = jest.fn((key, value) => {
        cookieStore[key] = value;
    });
    const loadItems = jest.fn(function() {
        return this.serverParams;
    });

    return {
        ...component,
        methods: {
            ...(component.methods || {}),
            getCookie,
            setCookie,
            loadItems
        },
        __testMocks: {
            getCookie,
            setCookie,
            loadItems
        }
    };
};

const mountHistoryComponent = (component, store, cookieStore, stubs) => {
    const localVue = createLocalVueForHistory();
    const mountedComponent = makeMountedHistoryComponent(component, cookieStore);
    const wrapper = shallowMount(mountedComponent, {
        localVue,
        store,
        stubs
    });
    wrapper.vm.loadItemsDebounced = jest.fn();
    return {
        component: mountedComponent,
        wrapper,
        ...mountedComponent.__testMocks
    };
};

const mountSharedHistoryComponents = store => {
    const cookieStore = {};
    const detailed = mountHistoryComponent(HistoryDetailed, store, cookieStore, {
        VueGoodTable: VueGoodTableStub,
        AppLink: true,
        QualityPill: true,
        FontAwesomeIcon: true,
        Multiselect: true
    });
    const compact = mountHistoryComponent(HistoryCompact, store, cookieStore, {
        VueGoodTable: VueGoodTableStub,
        AppLink: true,
        QualityPill: true
    });
    return {
        detailed: detailed.wrapper,
        compact: compact.wrapper,
        detailedMount: detailed,
        compactMount: compact
    };
};

const mountDetailed = (history = {}, cookieStore = {}) => {
    const store = createHistoryStore({ ...history, layout: 'detailed' });
    const mounted = mountHistoryComponent(HistoryDetailed, store, cookieStore, {
        VueGoodTable: VueGoodTableStub,
        AppLink: true,
        QualityPill: true,
        FontAwesomeIcon: true,
        Multiselect: true
    });
    return {
        store,
        cookieStore,
        ...mounted
    };
};

const mountCompact = (history = {}, cookieStore = {}) => {
    const store = createHistoryStore({ ...history, layout: 'compact' });
    const mounted = mountHistoryComponent(HistoryCompact, store, cookieStore, {
        VueGoodTable: VueGoodTableStub,
        AppLink: true,
        QualityPill: true
    });
    return {
        store,
        cookieStore,
        ...mounted
    };
};

const getPaginationOptions = wrapper => {
    const table = wrapper.vm.$children.find(child => {
        return child && child.$props && Object.prototype.hasOwnProperty.call(child.$props, 'paginationOptions');
    });
    return table && table.$props && table.$props.paginationOptions;
};

const detailedFilterDefaults = () => ({
    resource: 'old resource',
    providerId: 'old provider',
    quality: '720p',
    size: '< 1024',
    clientStatus: 1,
    statusName: 'Downloaded'
});

const detailedTextInput = field => field === 'resource' ? 'Show title or release' : 'Provider | Group';

const detailedTextMethod = field => field === 'resource' ? 'updateResource' : 'updateProvider';

const assertDetailedTextUpdate = async ({ field, value, expected, visibleValue = value, initialFilters = detailedFilterDefaults() }) => {
    const { wrapper } = mountDetailed({
        remote: {
            page: 9,
            filter: {
                columnFilters: initialFilters
            }
        }
    });
    wrapper.vm.loadItemsDebounced.mockClear();
    wrapper.vm[detailedTextMethod(field)]({
        currentTarget: {
            value
        }
    });
    await wrapper.vm.$nextTick();

    expect(wrapper.find(`input[placeholder="${detailedTextInput(field)}"]`).element.value).toBe(visibleValue);
    expect(wrapper.vm.remoteHistory.filter.columnFilters).toEqual({
        ...initialFilters,
        [field]: expected
    });
    expect(wrapper.vm.remoteHistory.page).toBe(1);
    expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
    wrapper.destroy();
};

const assertDetailedOtherFilter = async ({ method, event, field, expected }) => {
    const initialFilters = detailedFilterDefaults();
    const { wrapper } = mountDetailed({
        remote: {
            page: 9,
            filter: {
                columnFilters: initialFilters
            }
        }
    });
    wrapper.vm.updateResource({
        currentTarget: {
            value: "'  cleaned resource"
        }
    });
    wrapper.vm.loadItemsDebounced.mockClear();
    wrapper.vm[method](event);
    await wrapper.vm.$nextTick();

    expect(wrapper.find('input[placeholder="Show title or release"]').element.value).toBe('cleaned resource');
    expect(wrapper.vm.remoteHistory.filter.columnFilters).toEqual({
        ...initialFilters,
        resource: 'cleaned resource',
        [field]: expected
    });
    expect(wrapper.vm.remoteHistory.page).toBe(1);
    expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
    wrapper.destroy();
};

const assertCompactResourceUpdate = async ({ page, value, expected, existingFilters = {}, visibleValue = value }) => {
    const initialFilters = {
        resource: 'old compact',
        ...existingFilters
    };
    const { wrapper } = mountCompact({
        remoteCompact: {
            page,
            filter: {
                columnFilters: initialFilters
            }
        }
    });
    wrapper.vm.loadItemsDebounced.mockClear();
    wrapper.vm.updateResource({
        currentTarget: {
            value
        }
    });
    await wrapper.vm.$nextTick();

    expect(wrapper.find('input[placeholder="Show title or release"]').element.value).toBe(visibleValue);
    expect(wrapper.vm.remoteHistory.filter.columnFilters).toEqual({
        ...initialFilters,
        resource: expected
    });
    expect(wrapper.vm.remoteHistory.page).toBe(1);
    expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
    wrapper.destroy();
};

const matchingTextPairs = ["''", '""', '``'];

const assertDetailedPairEditing = async ({ field, pair }) => {
    const initialFilters = detailedFilterDefaults();
    const { wrapper } = mountDetailed({
        remote: {
            page: 9,
            filter: {
                columnFilters: initialFilters
            }
        }
    });
    const updateField = detailedTextMethod(field);
    const assertStage = async ({ value, filterValue, malformed }) => {
        wrapper.vm[updateField]({
            currentTarget: {
                value
            }
        });
        await wrapper.vm.$nextTick();

        expect(wrapper.find(`input[placeholder="${detailedTextInput(field)}"]`).element.value).toBe(value);
        expect(wrapper.vm.remoteHistory.filter.columnFilters[field]).toBe(filterValue);
        if (field === 'resource') {
            expect(wrapper.vm.episodeFilter).toMatchObject({
                inputValue: value,
                filterValue,
                malformed,
                initialized: true
            });
        } else {
            expect(wrapper.vm.providerFilterValue).toBe(value);
            expect(wrapper.vm.malformedTextFilters.providerId).toBe(malformed);
        }
    };
    const completedValue = `${pair[0]}matched${pair[1]}`;

    await assertStage({ value: pair[0], filterValue: '', malformed: true });
    await assertStage({ value: pair, filterValue: '', malformed: true });
    await assertStage({ value: completedValue, filterValue: completedValue, malformed: false });
    expect(wrapper.vm.remoteHistory.page).toBe(1);
    expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(3);
    wrapper.destroy();
};

const assertCompactPairEditing = async pair => {
    const { wrapper } = mountCompact({
        remoteCompact: {
            page: 4,
            filter: {
                columnFilters: {
                    resource: 'compact episode'
                }
            }
        }
    });
    const assertStage = async ({ value, filterValue, malformed }) => {
        wrapper.vm.updateResource({
            currentTarget: {
                value
            }
        });
        await wrapper.vm.$nextTick();

        expect(wrapper.find('input[placeholder="Show title or release"]').element.value).toBe(value);
        expect(wrapper.vm.remoteHistory.filter.columnFilters.resource).toBe(filterValue);
        expect(wrapper.vm.episodeFilter).toMatchObject({
            inputValue: value,
            filterValue,
            malformed,
            initialized: true
        });
    };
    const completedValue = `${pair[0]}matched${pair[1]}`;

    await assertStage({ value: pair[0], filterValue: '', malformed: true });
    await assertStage({ value: pair, filterValue: '', malformed: true });
    await assertStage({ value: completedValue, filterValue: completedValue, malformed: false });
    expect(wrapper.vm.remoteHistory.page).toBe(1);
    expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(3);
    wrapper.destroy();
};

const assertDetailedPairReset = async ({ field, pair, trigger, expectedPatch }) => {
    const initialFilters = detailedFilterDefaults();
    const { wrapper } = mountDetailed({
        remote: {
            page: 9,
            filter: {
                columnFilters: initialFilters
            }
        }
    });
    wrapper.vm[detailedTextMethod(field)]({
        currentTarget: {
            value: pair
        }
    });
    await wrapper.vm.$nextTick();

    expect(wrapper.find(`input[placeholder="${detailedTextInput(field)}"]`).element.value).toBe(pair);
    if (field === 'resource') {
        expect(wrapper.vm.episodeFilter.malformed).toBe(true);
    } else {
        expect(wrapper.vm.malformedTextFilters.providerId).toBe(true);
    }

    wrapper.vm.loadItemsDebounced.mockClear();
    trigger(wrapper.vm);
    await wrapper.vm.$nextTick();

    expect(wrapper.find(`input[placeholder="${detailedTextInput(field)}"]`).element.value).toBe('');
    expect(wrapper.vm.remoteHistory.filter.columnFilters[field]).toBe('');
    if (field === 'resource') {
        expect(wrapper.vm.episodeFilter).toMatchObject({
            inputValue: '',
            filterValue: '',
            malformed: false,
            initialized: true
        });
    } else {
        expect(wrapper.vm.providerFilterValue).toBe('');
        expect(wrapper.vm.malformedTextFilters.providerId).toBe(false);
    }
    Object.entries(expectedPatch).forEach(([key, value]) => {
        expect(wrapper.vm.remoteHistory.filter.columnFilters[key]).toEqual(value);
    });
    expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
    wrapper.destroy();
};

const assertHistoryPairSortReset = async ({ layout, field, pair, sortEvent }) => {
    const detailed = layout === 'detailed';
    const remote = {
        page: 4,
        filter: {
            columnFilters: detailed ? detailedFilterDefaults() : {
                resource: 'old compact'
            }
        }
    };
    const { wrapper } = detailed ? mountDetailed({ remote }) : mountCompact({ remoteCompact: remote });
    const inputPlaceholder = detailed ? detailedTextInput(field) : 'Show title or release';
    const updateField = detailed ? detailedTextMethod(field) : 'updateResource';
    wrapper.vm[updateField]({
        currentTarget: {
            value: pair
        }
    });
    await wrapper.vm.$nextTick();
    expect(wrapper.find(`input[placeholder="${inputPlaceholder}"]`).element.value).toBe(pair);

    wrapper.vm.loadItemsDebounced.mockClear();
    wrapper.vm.remoteHistory.page = 4;
    const table = wrapper.vm.$refs[detailed ? 'detailed-history' : 'compact-history'];
    table.emitSort(sortEvent);
    await wrapper.vm.$nextTick();

    expect(wrapper.vm.remoteHistory.filter.columnFilters[field]).toBe('');
    if (field === 'providerId') {
        expect(wrapper.vm.providerFilterValue).toBe('');
        expect(wrapper.vm.malformedTextFilters.providerId).toBe(false);
    } else {
        expect(wrapper.vm.episodeFilter).toMatchObject({
            inputValue: '',
            filterValue: '',
            malformed: false,
            initialized: true
        });
    }
    expect(wrapper.find(`input[placeholder="${inputPlaceholder}"]`).element.value).toBe('');
    expect(wrapper.vm.remoteHistory.page).toBe(4);
    expect(wrapper.vm.remoteHistory.sort).toEqual(sortEvent[0].type === 'none' ? [{
        field: 'actionDate',
        type: 'desc'
    }] : sortEvent);
    expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
    wrapper.destroy();
};

const assertEpisodePairLayoutReset = async ({ fromLayout, toLayout, pair }) => {
    const store = createHistoryStore({
        layout: fromLayout,
        remote: {
            filter: {
                columnFilters: {
                    resource: 'detailed episode'
                }
            }
        },
        remoteCompact: {
            filter: {
                columnFilters: {
                    resource: 'compact episode'
                }
            }
        }
    });
    const normalized = normalizeHistoryTextFilter(pair);
    store.commit('updateEpisodeFilter', {
        inputValue: pair,
        filterValue: normalized.filterValue,
        malformed: normalized.malformed
    });
    expect(store.state.history.episodeFilter).toMatchObject({
        inputValue: pair,
        filterValue: '',
        malformed: true,
        initialized: true
    });

    await store.dispatch('prepareHistoryLayoutTransition', { layout: toLayout });

    expect(store.state.history.episodeFilter).toMatchObject({
        inputValue: '',
        filterValue: '',
        malformed: false,
        initialized: true
    });
    expect(store.state.history.remote.filter.columnFilters.resource || '').toBe('');
    expect(store.state.history.remoteCompact.filter.columnFilters.resource || '').toBe('');
};

const assertProviderPairLayoutReset = async pair => {
    const { wrapper, store, cookieStore } = mountDetailed({
        remote: {
            filter: {
                columnFilters: detailedFilterDefaults()
            }
        }
    });
    wrapper.vm.updateProvider({
        currentTarget: {
            value: pair
        }
    });
    await wrapper.vm.$nextTick();
    expect(wrapper.find('input[placeholder="Provider | Group"]').element.value).toBe(pair);
    expect(wrapper.vm.malformedTextFilters.providerId).toBe(true);

    await store.dispatch('prepareHistoryLayoutTransition', { layout: 'compact' });
    expect(Object.prototype.hasOwnProperty.call(store.state.history.remote.filter.columnFilters, 'providerId')).toBe(false);
    expect(Object.prototype.hasOwnProperty.call(store.state.history.remoteCompact.filter.columnFilters, 'providerId')).toBe(false);
    store.state.config.layout.history = 'compact';
    wrapper.destroy();

    await store.dispatch('prepareHistoryLayoutTransition', { layout: 'detailed' });
    store.state.config.layout.history = 'detailed';
    const returnedDetailed = mountHistoryComponent(HistoryDetailed, store, cookieStore, {
        VueGoodTable: VueGoodTableStub,
        AppLink: true,
        QualityPill: true,
        FontAwesomeIcon: true,
        Multiselect: true
    });
    expect(returnedDetailed.wrapper.find('input[placeholder="Provider | Group"]').element.value).toBe('');
    expect(returnedDetailed.wrapper.vm.malformedTextFilters.providerId).toBe(false);
    returnedDetailed.wrapper.destroy();
};

describe('normalizeHistoryTextFilter', () => {
    it('covers text boundary, punctuation, and Unicode normalization cases', () => {
        const cases = [
            ['', '', false, false],
            ['   ', '', false, false],
            ['  unquoted title  ', 'unquoted title', false, false],
            ["'  quoted title  '", "'  quoted title  '", false, false],
            ['"  quoted title  "', '"  quoted title  "', false, false],
            ['`  quoted title  `', '`  quoted title  `', false, false],
            ["  ''  ", '', true, false],
            ['""', '', true, false],
            ['``', '', true, false],
            ["'", '', true, false],
            ["'leading", 'leading', true, false],
            ['trailing"', 'trailing', true, false],
            ["'mismatched\"", 'mismatched', true, false],
            ["''leading", 'leading', true, false],
            ['trailing""', 'trailing', true, false],
            ["''  repeated  \"", 'repeated', true, false],
            ["Test's", "Test's", false, false],
            ["Test ' s", "Test ' s", false, false],
            ['Test"s', 'Test"s', false, false],
            ['Test " s', 'Test " s', false, false],
            ['Test`s', 'Test`s', false, false],
            ['Test ` s', 'Test ` s', false, false],
            ['"Test\'s"', '"Test\'s"', false, false],
            ["'Test \" s'", "'Test \" s'", false, false],
            ["  `Test ' s`  ", "`Test ' s`", false, false],
            ["'Dog Days\"'", "'Dog Days\"'", false, false],
            ['"Dog Days\'"', '"Dog Days\'"', false, false],
            ["'\"Leading double quote'", "'\"Leading double quote'", false, false],
            ['  ’The “Ogre” Bride’  ', '’The “Ogre” Bride’', false, false],
            ['  「日本語の題名」  ', '「日本語の題名」', false, false],
            ['  『Provider』  ', '『Provider』', false, false]
        ];

        cases.forEach(([value, filterValue, malformed, clearInput]) => {
            expect(normalizeHistoryTextFilter(value)).toEqual({
                filterValue,
                malformed,
                clearInput
            });
        });
    });

    it('retains exactly one matching wrapper pair around repeated wrapper content', () => {
        const cases = [["'''", "'"], ["''''", "''"], ['"""', '"'], ['""""', '""'], ['```', '`'], ['````', '``']];

        cases.forEach(([value, inner]) => {
            const result = normalizeHistoryTextFilter(value);
            expect(result).toEqual({
                filterValue: value,
                malformed: false,
                clearInput: false
            });
            expect(result.filterValue.slice(1, -1)).toBe(inner);
        });
    });
});

describe('normalizeHistorySizeFilter', () => {
    it.each([
        ['<300', '< 300'],
        ['>400', '> 400'],
        ['>1.3gb', '> 1.3 GB'],
        ['<200mb', '< 200 MB'],
        ['>1.4 gb', '> 1.4 GB'],
        ['<900.45 MB', '< 900.45 MB'],
        ['>2.4GB', '> 2.4 GB'],
        ['>123456789.99', '> 123456789.99'],
        ['  "  >1.4 gb  "  ', '> 1.4 GB'],
        ['`<900.45 MB`', '< 900.45 MB'],
        ['<8589934591.99', '< 8589934591.99'],
        ['>8589934591.99 GB', '> 8589934591.99 GB']
    ])('normalizes valid Size grammar %s', (value, filterValue) => {
        expect(normalizeHistorySizeFilter(value)).toEqual({
            filterValue,
            valid: true,
            clearFilter: false
        });
    });

    it.each([
        '= 1024',
        '<= 1024',
        '>= 1024',
        '< 1024 OR 1=1',
        '< 1.345',
        '< 1.4.5',
        '< .5',
        '< 1.',
        '< 1024 TB',
        '123456789.99',
        '< 8589934592',
        '< 8589934591.999',
        "'< 1024\"",
        '<1024MB`'
    ])('rejects malformed or over-cap Size grammar %s', value => {
        expect(normalizeHistorySizeFilter(value)).toEqual({
            filterValue: '',
            valid: false,
            clearFilter: false
        });
    });

    it.each(['', '   ', "''", '""', '``', '  `  `  '])('marks empty Size forms for clearing: %j', value => {
        expect(normalizeHistorySizeFilter(value)).toEqual({
            filterValue: '',
            valid: false,
            clearFilter: true
        });
    });
});

describe('History filter state composition', () => {
    it.each([
        ['detailed', HistoryDetailed, 'remote', {
            AppLink: true,
            QualityPill: true,
            FontAwesomeIcon: true,
            Multiselect: true
        }],
        ['compact', HistoryCompact, 'remoteCompact', {
            AppLink: true,
            QualityPill: true
        }]
    ])('%s ignores the pre-mount page-one event but accepts mounted page changes', (_layout, component, remoteKey, componentStubs) => {
        const store = createHistoryStore({
            [remoteKey]: {
                page: 4
            }
        });
        const mounted = mountHistoryComponent(component, store, {}, {
            VueGoodTable: VueGoodTableInitialPageStub,
            ...componentStubs
        });

        expect(store.state.history[remoteKey].page).toBe(4);
        expect(mounted.loadItems.mock.results[0].value.page).toBe(4);

        mounted.wrapper.vm.loadItemsDebounced.mockClear();
        mounted.wrapper.vm.onPageChange({
            currentPage: 1
        });
        expect(mounted.wrapper.vm.remoteHistory.page).toBe(1);
        expect(mounted.wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);

        mounted.wrapper.vm.onPageChange({
            currentPage: 3
        });
        expect(mounted.wrapper.vm.remoteHistory.page).toBe(3);
        expect(mounted.wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(2);
        mounted.wrapper.destroy();
    });

    it('detailed onColumnFilter merges native and manual filters without persisting a filter cookie', () => {
        const { wrapper, setCookie } = mountDetailed({
            remote: {
                page: 4,
                filter: {
                    columnFilters: {
                        resource: 'The Show',
                        providerId: 'provider-a',
                        quality: '1080p',
                        size: '< 1024',
                        clientStatus: 5,
                        statusName: 'Downloaded'
                    }
                }
            }
        });

        setCookie.mockClear();
        wrapper.vm.loadItemsDebounced.mockClear();

        wrapper.vm.onColumnFilter({
            columnFilters: {
                statusName: 'Failed'
            }
        });

        expect(wrapper.vm.remoteHistory.page).toBe(1);
        expect(wrapper.vm.remoteHistory.filter).toEqual({
            columnFilters: {
                resource: 'The Show',
                providerId: 'provider-a',
                quality: '1080p',
                size: '< 1024',
                clientStatus: 5,
                statusName: 'Failed'
            }
        });
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        expect(setCookie).toHaveBeenCalledTimes(0);
        wrapper.destroy();
    });

    it('detailed pager options track page and remain on first page when episode/resource filter is set and cleared', async () => {
        const { wrapper } = mountDetailed({
            remote: {
                page: 4,
                filter: {
                    columnFilters: {
                        resource: 'The Show',
                        providerId: 'provider-a',
                        quality: '1080p',
                        size: '< 1024',
                        clientStatus: 5,
                        statusName: 'Downloaded'
                    }
                }
            }
        });

        wrapper.vm.loadItemsDebounced.mockClear();

        expect(getPaginationOptions(wrapper).setCurrentPage).toBe(4);

        wrapper.vm.onPageChange({
            currentPage: 2
        });
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.remoteHistory.page).toBe(2);
        expect(getPaginationOptions(wrapper).setCurrentPage).toBe(2);
        wrapper.vm.loadItemsDebounced.mockClear();

        wrapper.vm.updateResource({
            currentTarget: {
                value: 'new resource'
            }
        });
        expect(wrapper.vm.remoteHistory.page).toBe(1);
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        await wrapper.vm.$nextTick();
        expect(getPaginationOptions(wrapper).setCurrentPage).toBe(1);

        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.updateResource({
            currentTarget: {
                value: ''
            }
        });
        expect(wrapper.vm.remoteHistory.page).toBe(1);
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        await wrapper.vm.$nextTick();
        expect(getPaginationOptions(wrapper).setCurrentPage).toBe(1);
        wrapper.destroy();
    });

    it('detailed onColumnFilter keeps statusName cleared and fully resets native keys on empty map', () => {
        const { wrapper } = mountDetailed({
            remote: {
                page: 3,
                filter: {
                    columnFilters: {
                        resource: 'The Show',
                        providerId: 'provider-a',
                        quality: '1080p',
                        size: '< 1024',
                        clientStatus: 5,
                        statusName: 'Downloaded'
                    }
                }
            }
        });

        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.onColumnFilter({
            columnFilters: {
                statusName: ''
            }
        });
        expect(wrapper.vm.remoteHistory.filter.columnFilters).toEqual({
            resource: 'The Show',
            providerId: 'provider-a',
            quality: '1080p',
            size: '< 1024',
            clientStatus: 5,
            statusName: ''
        });
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        expect(wrapper.vm.remoteHistory.page).toBe(1);

        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.onColumnFilter({
            columnFilters: {}
        });
        expect(wrapper.vm.remoteHistory.filter.columnFilters).toEqual({
            resource: 'The Show',
            providerId: 'provider-a',
            quality: '1080p',
            size: '< 1024',
            clientStatus: 5
        });
        expect(wrapper.vm.remoteHistory.filter.columnFilters.statusName).toBeUndefined();
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        expect(wrapper.vm.remoteHistory.page).toBe(1);
        wrapper.destroy();
    });

    it('detailed manual filters preserve other fields and queue one load per valid update', () => {
        const { wrapper, setCookie } = mountDetailed({
            remote: {
                page: 9,
                filter: {
                    columnFilters: {
                        resource: 'old resource',
                        providerId: 'old provider',
                        quality: '720p',
                        size: '< 1024',
                        clientStatus: 1,
                        statusName: 'Downloaded'
                    }
                }
            }
        });
        setCookie.mockClear();

        wrapper.vm.updateResource({
            currentTarget: {
                value: 'new resource'
            }
        });
        expect(wrapper.vm.remoteHistory.page).toBe(1);
        expect(wrapper.vm.remoteHistory.filter.columnFilters).toEqual({
            resource: 'new resource',
            providerId: 'old provider',
            quality: '720p',
            size: '< 1024',
            clientStatus: 1,
            statusName: 'Downloaded'
        });
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);

        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.updateProvider({
            currentTarget: {
                value: 'new provider'
            }
        });
        expect(wrapper.vm.remoteHistory.filter.columnFilters.providerId).toBe('new provider');
        expect(wrapper.vm.remoteHistory.page).toBe(1);
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);

        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.updateQualityFilter({
            currentTarget: {
                value: '1080p'
            }
        });
        expect(wrapper.vm.remoteHistory.filter.columnFilters.quality).toBe('1080p');
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);

        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.updateClientStatusFilter([{
            value: 1
        }, {
            value: 2
        }]);
        expect(wrapper.vm.selectedClientStatusValue).toEqual([{
            value: 1
        }, {
            value: 2
        }]);
        expect(wrapper.vm.remoteHistory.filter.columnFilters.clientStatus).toBe(3);
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);

        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.updateSizeFilter({
            currentTarget: {
                value: '> 2048'
            }
        });
        expect(wrapper.vm.remoteHistory.filter.columnFilters.size).toBe('> 2048');
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);

        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.updateSizeFilter({
            currentTarget: {
                value: ''
            }
        });
        expect(wrapper.vm.remoteHistory.filter.columnFilters.size).toBe('');
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);

        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.updateSizeFilter({
            currentTarget: {
                value: 'abc'
            }
        });
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(0);
        expect(setCookie).toHaveBeenCalledTimes(0);
        wrapper.destroy();
    });

    it('detailed Client Status applies each supported value, combined masks, and a distinct clear', () => {
        const initialFilters = {
            resource: 'old resource',
            providerId: 'old provider',
            quality: '720p',
            size: '< 1024',
            statusName: 'Downloaded'
        };
        const { wrapper } = mountDetailed({
            remote: {
                page: 9,
                filter: {
                    columnFilters: initialFilters
                }
            }
        });
        const values = [0, 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024];

        values.forEach(value => {
            const option = clientStatusOption(value);
            wrapper.vm.loadItemsDebounced.mockClear();
            wrapper.vm.updateClientStatusFilter([option]);

            expect(wrapper.vm.selectedClientStatusValue).toEqual([option]);
            expect(wrapper.vm.selectedClientStatusValue[0]).toBe(option);
            expect(wrapper.vm.remoteHistory.filter.columnFilters.clientStatus).toBe(value);
            expect(wrapper.vm.remoteHistory.page).toBe(1);
            expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        });

        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.updateClientStatusFilter([]);
        expect(wrapper.vm.selectedClientStatusValue).toEqual([]);
        expect(wrapper.vm.remoteHistory.filter.columnFilters.clientStatus).toBe('');
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);

        const combinedOptions = [1, 2, 4].map(clientStatusOption);
        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.updateClientStatusFilter(combinedOptions);
        expect(wrapper.vm.selectedClientStatusValue).toEqual(combinedOptions);
        expect(wrapper.vm.remoteHistory.filter.columnFilters).toEqual({
            ...initialFilters,
            clientStatus: 7
        });
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        wrapper.destroy();
    });

    it('detailed Client Status keeps Snatched and nonzero selections mutually exclusive', () => {
        const { wrapper } = mountDetailed({
            remote: {
                page: 9,
                filter: {
                    columnFilters: {
                        resource: 'old resource',
                        providerId: 'old provider',
                        quality: '720p',
                        size: '< 1024',
                        statusName: 'Downloaded'
                    }
                }
            }
        });
        const snatched = clientStatusOption(0);
        const paused = clientStatusOption(1);
        const downloading = clientStatusOption(2);
        const completed = clientStatusOption(128);

        wrapper.vm.updateClientStatusFilter([paused, downloading]);
        expect(wrapper.vm.remoteHistory.filter.columnFilters.clientStatus).toBe(3);
        wrapper.vm.loadItemsDebounced.mockClear();

        wrapper.vm.updateClientStatusFilter([paused, downloading, snatched]);
        expect(wrapper.vm.selectedClientStatusValue).toEqual([snatched]);
        expect(wrapper.vm.selectedClientStatusValue[0]).toBe(snatched);
        expect(wrapper.vm.remoteHistory.filter.columnFilters.clientStatus).toBe(0);
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        wrapper.vm.loadItemsDebounced.mockClear();

        wrapper.vm.updateClientStatusFilter([snatched, completed]);
        expect(wrapper.vm.selectedClientStatusValue).toEqual([completed]);
        expect(wrapper.vm.selectedClientStatusValue[0]).toBe(completed);
        expect(wrapper.vm.remoteHistory.filter.columnFilters.clientStatus).toBe(128);
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        wrapper.destroy();
    });

    it.each([
        ['Snatched', 0, [0]],
        ['composed nonzero', 128 | 256, [128, 256]],
        ['cleared', '', []],
        ['missing', undefined, []],
        ['unsupported', 2048, []],
        ['negative', -1, []],
        ['non-integer', 1.5, []]
    ])('restores %s Client Status selections from the active filter', (_name, clientStatus, expectedValues) => {
        const columnFilters = {};
        if (clientStatus !== undefined) {
            columnFilters.clientStatus = clientStatus;
        }
        const { wrapper } = mountDetailed({
            remote: {
                filter: {
                    columnFilters
                }
            }
        });
        const expectedOptions = expectedValues.map(clientStatusOption);

        expect(wrapper.vm.selectedClientStatusValue).toEqual(expectedOptions);
        expectedOptions.forEach((option, index) => {
            expect(wrapper.vm.selectedClientStatusValue[index]).toBe(option);
        });
        wrapper.destroy();
    });

    it('detailed Client Status preserves explicit zero through native filter and sort commits', async () => {
        const { wrapper } = mountDetailed({
            remote: {
                page: 9,
                filter: {
                    columnFilters: {
                        resource: 'old resource',
                        providerId: 'old provider',
                        quality: '720p',
                        size: '< 1024',
                        statusName: 'Downloaded'
                    }
                }
            }
        });
        wrapper.vm.updateClientStatusFilter([clientStatusOption(0)]);

        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.onColumnFilter({
            columnFilters: {
                statusName: 'Failed'
            }
        });
        expect(wrapper.vm.remoteHistory.filter.columnFilters.clientStatus).toBe(0);
        expect(wrapper.vm.remoteHistory.filter.columnFilters.statusName).toBe('Failed');
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);

        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.$refs['detailed-history'].emitSort([{ field: 'quality', type: 'asc' }]);
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.remoteHistory.filter.columnFilters.clientStatus).toBe(0);
        expect(wrapper.vm.remoteHistory.sort).toEqual([{ field: 'quality', type: 'asc' }]);
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        wrapper.destroy();
    });

    it('detailed provider filter trims outer whitespace and preserves the filter stack', () => {
        const initialFilters = {
            resource: 'old resource',
            providerId: 'old provider',
            quality: '720p',
            size: '< 1024',
            clientStatus: 1,
            statusName: 'Downloaded'
        };
        const { wrapper } = mountDetailed({
            remote: {
                page: 9,
                filter: {
                    columnFilters: initialFilters
                }
            }
        });
        const cases = [
            {
                value: '  leading provider',
                expected: 'leading provider'
            },
            {
                value: 'trailing provider  ',
                expected: 'trailing provider'
            },
            {
                value: '  both sides provider  ',
                expected: 'both sides provider'
            },
            {
                value: '   ',
                expected: ''
            }
        ];

        cases.forEach(({ value, expected }) => {
            wrapper.vm.loadItemsDebounced.mockClear();
            wrapper.vm.updateProvider({
                currentTarget: {
                    value
                }
            });
            expect(wrapper.vm.remoteHistory.filter.columnFilters).toEqual({
                ...initialFilters,
                providerId: expected
            });
            expect(wrapper.vm.remoteHistory.page).toBe(1);
            expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        });
        wrapper.destroy();
    });

    it('detailed episode and provider filters preserve quoted backend values', async () => {
        const { wrapper } = mountDetailed();

        wrapper.vm.updateResource({
            currentTarget: {
                value: "'  quoted episode  '"
            }
        });
        expect(wrapper.vm.remoteHistory.filter.columnFilters.resource).toBe("'  quoted episode  '");
        await wrapper.vm.$nextTick();
        expect(wrapper.find('input[placeholder="Show title or release"]').element.value).toBe("'  quoted episode  '");

        wrapper.vm.updateResource({
            currentTarget: {
                value: 'plain episode'
            }
        });
        expect(wrapper.vm.remoteHistory.filter.columnFilters.resource).toBe('plain episode');

        wrapper.vm.updateProvider({
            currentTarget: {
                value: '  "  quoted provider  "  '
            }
        });
        expect(wrapper.vm.remoteHistory.filter.columnFilters.providerId).toBe('"  quoted provider  "');
        await wrapper.vm.$nextTick();
        expect(wrapper.find('input[placeholder="Provider | Group"]').element.value).toBe('  "  quoted provider  "  ');

        wrapper.vm.updateProvider({
            currentTarget: {
                value: 'plain provider'
            }
        });
        expect(wrapper.vm.remoteHistory.filter.columnFilters.providerId).toBe('plain provider');
        wrapper.destroy();
    });

    it('detailed text inputs reflect existing remote filters on mount', async () => {
        const { wrapper } = mountDetailed({
            remote: {
                filter: {
                    columnFilters: {
                        resource: 'stored episode',
                        providerId: 'stored provider'
                    }
                }
            }
        });

        await wrapper.vm.$nextTick();
        expect([
            wrapper.find('input[placeholder="Show title or release"]').element.value,
            wrapper.find('input[placeholder="Provider | Group"]').element.value
        ]).toEqual(['stored episode', 'stored provider']);
        wrapper.destroy();
    });

    it('detailed text filters keep malformed wrappers raw-visible while storing cleaned values', () => {
        expect.assertions(8);
        const cases = [
            ['resource', "'  leading only", 'leading only'],
            ['providerId', 'trailing only"  ', 'trailing only']
        ];
        return Promise.all(cases.map(([field, value, expected]) => assertDetailedTextUpdate({
            field,
            value,
            expected
        })));
    });

    it('detailed text filters preserve matching wrappers, inner spaces, and internal punctuation', () => {
        expect.assertions(16);
        const cases = [
            ['resource', "'  The Ogre's Bride  '", "'  The Ogre's Bride  '"],
            ['providerId', '  "  Provider Group  "  ', '"  Provider Group  "'],
            ['resource', '  "  Dog Days\'  "  ', '"  Dog Days\'  "'],
            ['providerId', '  plain provider  ', 'plain provider']
        ];
        return Promise.all(cases.map(([field, value, expected]) => assertDetailedTextUpdate({
            field,
            value,
            expected
        })));
    });

    it('keeps all detailed quote-pair forms editable until content completes them', () => {
        expect.hasAssertions();
        return Promise.all(['resource', 'providerId'].flatMap(field => matchingTextPairs.map(pair => {
            return assertDetailedPairEditing({ field, pair });
        })));
    });

    it('detailed successful manual filters canonicalize malformed text while preserving the stack', () => {
        expect.assertions(16);
        const cases = [
            ['updateQualityFilter', { currentTarget: { value: '1080p' } }, 'quality', '1080p'],
            ['updateSizeFilter', { currentTarget: { value: '  > 2048  ' } }, 'size', '> 2048'],
            ['updateSizeFilter', { currentTarget: { value: '   ' } }, 'size', ''],
            ['updateClientStatusFilter', [{ value: 1 }, { value: 2 }], 'clientStatus', 3]
        ];
        return Promise.all(cases.map(([method, event, field, expected]) => assertDetailedOtherFilter({
            method,
            event,
            field,
            expected
        })));
    });

    it('detailed cross-text and native filters canonicalize malformed inputs once', async () => {
        const initialFilters = {
            resource: 'old resource',
            providerId: 'old provider',
            quality: '720p',
            size: '< 1024',
            clientStatus: 1,
            statusName: 'Downloaded'
        };
        const { wrapper, setCookie } = mountDetailed({
            remote: {
                page: 9,
                filter: {
                    columnFilters: initialFilters
                }
            }
        });

        wrapper.vm.updateResource({
            currentTarget: {
                value: "'  cleaned resource"
            }
        });
        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.updateProvider({
            currentTarget: {
                value: '  "  provider group  "  '
            }
        });
        expect(wrapper.vm.remoteHistory.filter.columnFilters).toEqual({
            ...initialFilters,
            resource: 'cleaned resource',
            providerId: '"  provider group  "'
        });
        await wrapper.vm.$nextTick();
        expect(wrapper.find('input[placeholder="Show title or release"]').element.value).toBe('cleaned resource');
        expect(wrapper.find('input[placeholder="Provider | Group"]').element.value).toBe('  "  provider group  "  ');
        expect(wrapper.vm.remoteHistory.page).toBe(1);
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);

        wrapper.vm.updateProvider({
            currentTarget: {
                value: "'  cleaned provider"
            }
        });
        wrapper.vm.loadItemsDebounced.mockClear();
        setCookie.mockClear();
        wrapper.vm.onColumnFilter({
            columnFilters: {
                statusName: 'Failed'
            }
        });

        return wrapper.vm.$nextTick().then(() => {
            expect(wrapper.find('input[placeholder="Provider | Group"]').element.value).toBe('cleaned provider');
            expect(wrapper.vm.remoteHistory.filter.columnFilters).toEqual({
                ...initialFilters,
                resource: 'cleaned resource',
                providerId: 'cleaned provider',
                statusName: 'Failed'
            });
            expect(wrapper.vm.remoteHistory.page).toBe(1);
            expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
            expect(setCookie).toHaveBeenCalledTimes(0);
            wrapper.destroy();
        });
    });

    it.each([
        ['Episode on Provider input', 'resource', vm => vm.updateProvider({ currentTarget: { value: 'cross provider' } }), { providerId: 'cross provider' }],
        ['Provider on Episode input', 'providerId', vm => vm.updateResource({ currentTarget: { value: 'cross episode' } }), { resource: 'cross episode' }],
        ['Episode on Action filter', 'resource', vm => vm.onColumnFilter({ columnFilters: { statusName: 'Failed' } }), { statusName: 'Failed' }],
        ['Provider on Action filter', 'providerId', vm => vm.onColumnFilter({ columnFilters: { statusName: 'Failed' } }), { statusName: 'Failed' }],
        ['Episode on Quality filter', 'resource', vm => vm.updateQualityFilter({ currentTarget: { value: '1080p' } }), { quality: '1080p' }],
        ['Provider on Quality filter', 'providerId', vm => vm.updateQualityFilter({ currentTarget: { value: '1080p' } }), { quality: '1080p' }],
        ['Episode on Size filter', 'resource', vm => vm.updateSizeFilter({ currentTarget: { value: '> 2048' } }), { size: '> 2048' }],
        ['Provider on Size filter', 'providerId', vm => vm.updateSizeFilter({ currentTarget: { value: '> 2048' } }), { size: '> 2048' }],
        ['Episode on Client Status filter', 'resource', vm => vm.updateClientStatusFilter([{ value: 1 }, { value: 2 }]), { clientStatus: 3 }],
        ['Provider on Client Status filter', 'providerId', vm => vm.updateClientStatusFilter([{ value: 1 }, { value: 2 }]), { clientStatus: 3 }]
    ])('canonicalizes every empty quote pair for %s', async (_name, field, trigger, expectedPatch) => {
        expect.hasAssertions();
        await Promise.all(matchingTextPairs.map(pair => assertDetailedPairReset({
            field,
            pair,
            trigger,
            expectedPatch
        })));
    });

    it('detailed size filter canonicalizes valid values, including quoted values', () => {
        const initialFilters = {
            resource: 'old resource',
            providerId: 'old provider',
            quality: '720p',
            size: '< 1024',
            clientStatus: 1,
            statusName: 'Downloaded'
        };
        const { wrapper } = mountDetailed({
            remote: {
                page: 9,
                filter: {
                    columnFilters: initialFilters
                }
            }
        });
        const cases = [
            {
                value: '<1024',
                expected: '< 1024'
            },
            {
                value: '< 1024',
                expected: '< 1024'
            },
            {
                value: '  > 1024',
                expected: '> 1024'
            },
            {
                value: '> 1024  ',
                expected: '> 1024'
            },
            {
                value: '  > 1024  ',
                expected: '> 1024'
            },
            {
                value: "  '<1024'  ",
                expected: '< 1024'
            },
            {
                value: '  "> 8"  ',
                expected: '> 8'
            },
            {
                value: '`< 1`',
                expected: '< 1'
            },
            {
                value: '   ',
                expected: ''
            }
        ];

        cases.forEach(({ value, expected }) => {
            wrapper.vm.loadItemsDebounced.mockClear();
            wrapper.vm.updateSizeFilter({
                currentTarget: {
                    value
                }
            });
            expect(wrapper.vm.remoteHistory.filter.columnFilters).toEqual({
                ...initialFilters,
                size: expected
            });
            expect(wrapper.vm.remoteHistory.page).toBe(1);
            expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        });
        expect(wrapper.vm.remoteHistory.filter.columnFilters.size).toBe('');
        wrapper.destroy();
    });

    it('detailed size filter rejects invalid values without changing state or loading', () => {
        const initialFilters = {
            resource: 'old resource',
            providerId: 'old provider',
            quality: '720p',
            size: '> 8',
            clientStatus: 1,
            statusName: 'Downloaded'
        };
        const { wrapper, setCookie } = mountDetailed({
            remote: {
                page: 9,
                filter: {
                    columnFilters: initialFilters
                }
            }
        });
        const filterBefore = JSON.parse(JSON.stringify(wrapper.vm.remoteHistory.filter));
        const invalidValues = [
            '= 1024',
            '<= 1024',
            '>= 1024',
            '< 1.345',
            '< 1024 OR 1=1',
            '< 12345678901',
            "'< 1024\""
        ];

        invalidValues.forEach(value => {
            wrapper.vm.loadItemsDebounced.mockClear();
            setCookie.mockClear();
            wrapper.vm.updateSizeFilter({
                currentTarget: {
                    value
                }
            });
            expect(wrapper.vm.remoteHistory.filter).toEqual(filterBefore);
            expect(wrapper.vm.remoteHistory.page).toBe(9);
            expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(0);
            expect(setCookie).toHaveBeenCalledTimes(0);
        });
        wrapper.destroy();
    });

    it('detailed invalid size input leaves malformed text visible and does not reload', async () => {
        const { wrapper } = mountDetailed();
        const malformedResource = "'  still editing";
        wrapper.vm.updateResource({
            currentTarget: {
                value: malformedResource
            }
        });
        await wrapper.vm.$nextTick();
        const filterBefore = JSON.parse(JSON.stringify(wrapper.vm.remoteHistory.filter));
        wrapper.vm.loadItemsDebounced.mockClear();

        wrapper.vm.updateSizeFilter({
            currentTarget: {
                value: '<= 1024'
            }
        });
        await wrapper.vm.$nextTick();

        expect(wrapper.find('input[placeholder="Show title or release"]').element.value).toBe(malformedResource);
        expect(wrapper.vm.remoteHistory.filter).toEqual(filterBefore);
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(0);
        wrapper.destroy();
    });

    it('detailed size filter clears matching quote-only values for each wrapper', () => {
        const { wrapper } = mountDetailed({
            remote: {
                filter: {
                    columnFilters: {
                        size: '> 8'
                    }
                }
            }
        });
        const quoteOnlyValues = ["''", '""', '``', "  ''  "];

        quoteOnlyValues.forEach(value => {
            wrapper.vm.loadItemsDebounced.mockClear();
            wrapper.vm.updateSizeFilter({
                currentTarget: {
                    value
                }
            });
            expect(wrapper.vm.remoteHistory.filter.columnFilters.size).toBe('');
            expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        });
        wrapper.destroy();
    });

    it('detailed Size input starts from the active canonical filter and keeps valid raw typing visible', async () => {
        const { wrapper } = mountDetailed({
            remote: {
                page: 9,
                filter: {
                    columnFilters: {
                        size: '> 400'
                    }
                }
            }
        });
        const sizeInput = wrapper.findAll('input').at(2);

        expect(sizeInput.element.value).toBe('> 400');
        wrapper.vm.loadItemsDebounced.mockClear();
        const rawValue = '  >1.3gb  ';
        wrapper.vm.updateSizeFilter({
            currentTarget: {
                value: rawValue
            }
        });
        await wrapper.vm.$nextTick();

        expect(sizeInput.element.value).toBe(rawValue);
        expect(wrapper.vm.sizeFilterPendingCleanup).toBe(false);
        expect(wrapper.vm.remoteHistory.filter.columnFilters.size).toBe('> 1.3 GB');
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        wrapper.destroy();
    });

    it('detailed invalid Size input stays raw and leaves the applied filter, page, and request unchanged', async () => {
        const { wrapper } = mountDetailed({
            remote: {
                page: 7,
                filter: {
                    columnFilters: {
                        size: '> 400'
                    }
                }
            }
        });
        const sizeInput = wrapper.findAll('input').at(2);
        const filterBefore = JSON.parse(JSON.stringify(wrapper.vm.remoteHistory.filter));
        wrapper.vm.loadItemsDebounced.mockClear();
        const rawValue = '< 1.4.5';
        wrapper.vm.updateSizeFilter({
            currentTarget: {
                value: rawValue
            }
        });
        await wrapper.vm.$nextTick();

        expect(sizeInput.element.value).toBe(rawValue);
        expect(wrapper.vm.sizeFilterPendingCleanup).toBe(true);
        expect(wrapper.vm.remoteHistory.filter).toEqual(filterBefore);
        expect(wrapper.vm.remoteHistory.page).toBe(7);
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(0);
        wrapper.destroy();
    });

    it.each([
        ['Episode', vm => vm.updateResource({ currentTarget: { value: 'new episode' } })],
        ['Provider', vm => vm.updateProvider({ currentTarget: { value: 'new provider' } })],
        ['Action', vm => vm.onColumnFilter({ columnFilters: { statusName: 'Failed' } })],
        ['Quality', vm => vm.updateQualityFilter({ currentTarget: { value: '1080p' } })],
        ['Client Status', vm => vm.updateClientStatusFilter([{ value: 1 }, { value: 2 }])]
    ])('restores the applied Size value on %s filter commit with only the triggering request', async (_name, trigger) => {
        const { wrapper } = mountDetailed({
            remote: {
                page: 4,
                filter: {
                    columnFilters: {
                        size: '> 400'
                    }
                }
            }
        });
        const sizeInput = wrapper.findAll('input').at(2);
        wrapper.vm.updateSizeFilter({
            currentTarget: {
                value: '>1.3.5gb'
            }
        });
        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.remoteHistory.page = 4;

        trigger(wrapper.vm);
        await wrapper.vm.$nextTick();

        expect(sizeInput.element.value).toBe('> 400');
        expect(wrapper.vm.sizeFilterPendingCleanup).toBe(false);
        expect(wrapper.vm.remoteHistory.filter.columnFilters.size).toBe('> 400');
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        wrapper.destroy();
    });

    it.each([
        ['active', [{ field: 'quality', type: 'asc' }]],
        ['clear-to-default', [{ field: 'actionDate', type: 'none' }]]
    ])('restores the applied Size value on Detailed %s sort with only one request', async (_name, sortEvent) => {
        const { wrapper } = mountDetailed({
            remote: {
                page: 4,
                filter: {
                    columnFilters: {
                        size: '> 400'
                    }
                }
            }
        });
        const sizeInput = wrapper.findAll('input').at(2);
        wrapper.vm.updateSizeFilter({
            currentTarget: {
                value: '>1.3.5gb'
            }
        });
        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.remoteHistory.page = 4;

        wrapper.vm.$refs['detailed-history'].emitSort(sortEvent);
        await wrapper.vm.$nextTick();

        expect(sizeInput.element.value).toBe('> 400');
        expect(wrapper.vm.sizeFilterPendingCleanup).toBe(false);
        expect(wrapper.vm.remoteHistory.filter.columnFilters.size).toBe('> 400');
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        wrapper.destroy();
    });

    it('keeps valid raw Size input visible through a filter commit while using its canonical filter value', async () => {
        const { wrapper } = mountDetailed({
            remote: {
                filter: {
                    columnFilters: {
                        size: '> 400'
                    }
                }
            }
        });
        const sizeInput = wrapper.findAll('input').at(2);
        const rawValue = '  >1.3gb  ';

        wrapper.vm.updateSizeFilter({
            currentTarget: {
                value: rawValue
            }
        });
        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.updateQualityFilter({ currentTarget: { value: '1080p' } });
        await wrapper.vm.$nextTick();

        expect(sizeInput.element.value).toBe(rawValue);
        expect(wrapper.vm.sizeFilterPendingCleanup).toBe(false);
        expect(wrapper.vm.remoteHistory.filter.columnFilters.size).toBe('> 1.3 GB');
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        wrapper.destroy();
    });

    it('clears Size filter semantics while retaining whitespace and quote-only raw input until another filter commits', async () => {
        const { wrapper } = mountDetailed({
            remote: {
                filter: {
                    columnFilters: {
                        size: '> 400'
                    }
                }
            }
        });
        const sizeInput = wrapper.findAll('input').at(2);

        for (const rawValue of ['   ', "''"]) {
            wrapper.vm.loadItemsDebounced.mockClear();
            wrapper.vm.updateSizeFilter({
                currentTarget: {
                    value: rawValue
                }
            });

            expect(wrapper.vm.sizeFilterInputValue).toBe(rawValue);
            expect(wrapper.vm.sizeFilterPendingCleanup).toBe(true);
            expect(wrapper.vm.remoteHistory.filter.columnFilters.size).toBe('');
            expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        }

        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.updateQualityFilter({ currentTarget: { value: '1080p' } });
        await wrapper.vm.$nextTick();
        expect(sizeInput.element.value).toBe('');
        expect(wrapper.vm.sizeFilterPendingCleanup).toBe(false);
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        wrapper.destroy();
    });

    it('does not carry component-local Size input through Detailed to Compact and back', async () => {
        const store = createHistoryStore({
            layout: 'detailed',
            remote: {
                filter: {
                    columnFilters: {
                        size: '> 400'
                    }
                }
            },
            remoteCompact: {
                filter: {
                    columnFilters: {
                        size: '> 400'
                    }
                }
            }
        });
        const detailed = mountHistoryComponent(HistoryDetailed, store, {}, {
            VueGoodTable: VueGoodTableStub,
            AppLink: true,
            QualityPill: true,
            FontAwesomeIcon: true,
            Multiselect: true
        });
        detailed.wrapper.vm.updateSizeFilter({
            currentTarget: {
                value: '>1.3gb'
            }
        });
        await store.dispatch('prepareHistoryLayoutTransition', { layout: 'compact' });
        store.state.config.layout.history = 'compact';
        expect(store.state.history.remote.filter.columnFilters).toEqual({});
        expect(store.state.history.remoteCompact.filter.columnFilters).toEqual({});
        detailed.wrapper.destroy();

        const compact = mountHistoryComponent(HistoryCompact, store, {}, {
            VueGoodTable: VueGoodTableStub,
            AppLink: true,
            QualityPill: true
        });
        compact.wrapper.destroy();
        await store.dispatch('prepareHistoryLayoutTransition', { layout: 'detailed' });
        store.state.config.layout.history = 'detailed';

        const returnedDetailed = mountHistoryComponent(HistoryDetailed, store, {}, {
            VueGoodTable: VueGoodTableStub,
            AppLink: true,
            QualityPill: true,
            FontAwesomeIcon: true,
            Multiselect: true
        });
        expect(returnedDetailed.wrapper.findAll('input').at(2).element.value).toBe('');
        returnedDetailed.wrapper.destroy();
    });

    it('detailed manual update from null filter is safe', () => {
        const { wrapper } = mountDetailed({
            remote: {
                page: 6,
                filter: null
            }
        });

        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.updateProvider({
            currentTarget: {
                value: 'provider-null-safe'
            }
        });

        expect(wrapper.vm.remoteHistory.filter).toEqual({
            columnFilters: {
                resource: '',
                providerId: 'provider-null-safe'
            }
        });
        expect(wrapper.vm.remoteHistory.page).toBe(1);
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        wrapper.destroy();
    });

    it('compact resource filter preserves existing keys and synchronizes both Episode filters', async () => {
        const sharedHistory = {
            remote: {
                page: 10,
                filter: {
                    columnFilters: {
                        resource: 'old compact',
                        statusName: 'Downloaded',
                        other: 'detail only'
                    }
                }
            },
            remoteCompact: {
                page: 7,
                filter: {
                    columnFilters: {
                        resource: 'old compact'
                    }
                }
            }
        };
        const localVue = createLocalVueForHistory();
        const store = createHistoryStore(sharedHistory);
        const cookieStore = {};
        const detailedComponent = makeMountedHistoryComponent(HistoryDetailed, cookieStore);
        const compactComponent = makeMountedHistoryComponent(HistoryCompact, cookieStore);

        const detailed = shallowMount(detailedComponent, {
            localVue,
            store,
            stubs: {
                VueGoodTable: VueGoodTableStub,
                AppLink: true,
                QualityPill: true,
                FontAwesomeIcon: true,
                Multiselect: true
            }
        });
        const compact = shallowMount(compactComponent, {
            localVue,
            store,
            stubs: {
                VueGoodTable: VueGoodTableStub,
                AppLink: true,
                QualityPill: true
            }
        });
        const compactSetCookie = compactComponent.__testMocks.setCookie;
        const detailedSetCookie = detailedComponent.__testMocks.setCookie;
        compactSetCookie.mockClear();
        detailedSetCookie.mockClear();

        detailed.vm.loadItemsDebounced = jest.fn();
        compact.vm.loadItemsDebounced = jest.fn();

        await compact.vm.$nextTick();
        expect(compact.find('input[placeholder="Show title or release"]').element.value).toBe('old compact');
        expect(getPaginationOptions(compact).setCurrentPage).toBe(7);
        expect(getPaginationOptions(detailed).setCurrentPage).toBe(10);

        compact.vm.updateResource({
            currentTarget: {
                value: 'new compact'
            }
        });
        await compact.vm.$nextTick();

        expect(compact.vm.remoteHistory.page).toBe(1);
        expect(compact.vm.remoteHistory.filter.columnFilters).toEqual({
            resource: 'new compact'
        });
        expect(detailed.vm.remoteHistory.page).toBe(1);
        expect(detailed.vm.remoteHistory.filter).toEqual({
            columnFilters: {
                resource: 'new compact',
                statusName: 'Downloaded',
                other: 'detail only'
            }
        });
        await compact.vm.$nextTick();
        expect(getPaginationOptions(compact).setCurrentPage).toBe(1);
        expect(getPaginationOptions(detailed).setCurrentPage).toBe(1);
        expect(compact.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        expect(detailed.vm.loadItemsDebounced).toHaveBeenCalledTimes(0);
        expect(compactSetCookie).toHaveBeenCalledTimes(0);
        expect(detailedSetCookie).toHaveBeenCalledTimes(0);
        detailed.destroy();
        compact.destroy();
    });

    it('compact resource filter trims unquoted input while retaining the raw value', async () => {
        expect.assertions(4);
        await assertCompactResourceUpdate({
            page: 6,
            value: '  compact title  ',
            expected: 'compact title'
        });
    });

    it('compact resource filter stores cleaned malformed input while retaining its raw value', async () => {
        expect.assertions(4);
        await assertCompactResourceUpdate({
            page: 4,
            value: "  'compact malformed",
            expected: 'compact malformed'
        });
    });

    it('compact resource filter preserves non-empty matching wrappers and inner spaces', async () => {
        expect.assertions(4);
        await assertCompactResourceUpdate({
            page: 3,
            value: '  "  compact title  "  ',
            expected: '"  compact title  "'
        });
    });

    it('keeps all compact quote-pair forms editable until content completes them', async () => {
        expect.hasAssertions();
        await Promise.all(matchingTextPairs.map(pair => assertCompactPairEditing(pair)));
    });

    it('detailed Episode edits synchronize both layouts and only load detailed', async () => {
        const sharedHistory = {
            remote: {
                page: 5,
                filter: {
                    columnFilters: {
                        resource: 'detailed-only',
                        providerId: 'detailed-provider',
                        clientStatus: 1,
                        quality: '720p',
                        size: '< 500',
                        statusName: 'Downloaded'
                    }
                }
            },
            remoteCompact: {
                page: 8,
                filter: {
                    columnFilters: {
                        resource: 'compact-only'
                    }
                }
            }
        };
        const store = createHistoryStore(sharedHistory);
        const { detailed, compact } = mountSharedHistoryComponents(store);

        detailed.vm.loadItemsDebounced = jest.fn();
        compact.vm.loadItemsDebounced = jest.fn();

        await compact.vm.$nextTick();
        expect(getPaginationOptions(detailed).setCurrentPage).toBe(5);
        expect(getPaginationOptions(compact).setCurrentPage).toBe(8);
        detailed.vm.updateResource({
            currentTarget: {
                value: 'detailed-updated'
            }
        });
        await detailed.vm.$nextTick();
        expect(detailed.vm.remoteHistory.filter.columnFilters.resource).toBe('detailed-updated');
        expect(compact.vm.remoteHistory.page).toBe(1);
        expect(compact.vm.remoteHistory.filter.columnFilters).toEqual({
            resource: 'detailed-updated'
        });
        expect(detailed.vm.remoteHistory.page).toBe(1);
        expect(detailed.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        expect(compact.vm.loadItemsDebounced).toHaveBeenCalledTimes(0);
        compact.destroy();
        detailed.destroy();
    });

    it('compact Episode edits synchronize both layouts and only load compact', async () => {
        const sharedHistory = {
            remote: {
                page: 5,
                filter: {
                    columnFilters: {
                        resource: 'detailed-only',
                        providerId: 'detailed-provider',
                        clientStatus: 1,
                        quality: '720p',
                        size: '< 500',
                        statusName: 'Downloaded'
                    }
                }
            },
            remoteCompact: {
                page: 8,
                filter: {
                    columnFilters: {
                        resource: 'compact-only'
                    }
                }
            }
        };
        const store = createHistoryStore(sharedHistory);
        const { detailed, compact } = mountSharedHistoryComponents(store);

        detailed.vm.loadItemsDebounced = jest.fn();
        compact.vm.loadItemsDebounced = jest.fn();

        await compact.vm.$nextTick();
        expect(getPaginationOptions(compact).setCurrentPage).toBe(8);
        expect(getPaginationOptions(detailed).setCurrentPage).toBe(5);
        compact.vm.updateResource({
            currentTarget: {
                value: 'compact-updated'
            }
        });
        await compact.vm.$nextTick();
        expect(compact.vm.remoteHistory.filter.columnFilters.resource).toBe('compact-updated');
        expect(compact.vm.remoteHistory.page).toBe(1);
        expect(detailed.vm.remoteHistory.page).toBe(1);
        expect(detailed.vm.remoteHistory.filter.columnFilters).toEqual({
            resource: 'compact-updated',
            providerId: 'detailed-provider',
            clientStatus: 1,
            quality: '720p',
            size: '< 500',
            statusName: 'Downloaded'
        });
        expect(getPaginationOptions(compact).setCurrentPage).toBe(1);
        expect(getPaginationOptions(detailed).setCurrentPage).toBe(1);
        expect(detailed.vm.loadItemsDebounced).toHaveBeenCalledTimes(0);
        expect(compact.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        compact.destroy();
        detailed.destroy();
    });

    it('compact onColumnFilter keeps Episode and discards unsupported native keys', () => {
        const { wrapper, setCookie } = mountCompact({
            remoteCompact: {
                page: 6,
                filter: {
                    columnFilters: {
                        resource: 'compact show'
                    }
                }
            }
        });
        setCookie.mockClear();

        wrapper.vm.onColumnFilter({
            columnFilters: {
                statusName: 'Failed',
                providerId: 'discarded-provider',
                clientStatus: 3
            }
        });

        expect(wrapper.vm.remoteHistory.filter.columnFilters).toEqual({
            resource: 'compact show'
        });
        expect(wrapper.vm.remoteHistory.page).toBe(1);
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);

        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.onColumnFilter({
            columnFilters: {}
        });
        expect(wrapper.vm.remoteHistory.filter.columnFilters).toEqual({
            resource: 'compact show'
        });
        expect(wrapper.vm.remoteHistory.page).toBe(1);
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        expect(setCookie).toHaveBeenCalledTimes(0);
        wrapper.destroy();
    });

    it('canonicalizes malformed shared Episode values on layout transition', async () => {
        const rawEpisode = "  'Round trip episode";
        const cleanEpisode = 'Round trip episode';
        const store = createHistoryStore({
            layout: 'detailed',
            remote: {
                page: 4,
                filter: {
                    columnFilters: {
                        resource: 'initial episode',
                        statusName: 'Downloaded',
                        providerId: 'provider-a',
                        quality: '1',
                        size: '< 1024',
                        clientStatus: 3
                    }
                }
            },
            remoteCompact: {
                page: 7,
                filter: {
                    columnFilters: {
                        resource: 'stale episode',
                        statusName: 'Failed'
                    }
                }
            }
        });
        const cookieStore = {};
        const detailed = mountHistoryComponent(HistoryDetailed, store, cookieStore, {
            VueGoodTable: VueGoodTableStub,
            AppLink: true,
            QualityPill: true,
            FontAwesomeIcon: true,
            Multiselect: true
        });

        detailed.wrapper.vm.updateResource({
            currentTarget: {
                value: rawEpisode
            }
        });
        await detailed.wrapper.vm.$nextTick();

        expect(store.state.history.episodeFilter).toEqual({
            inputValue: rawEpisode,
            filterValue: cleanEpisode,
            malformed: true,
            initialized: true
        });
        expect(store.state.history.remote.page).toBe(1);
        expect(store.state.history.remoteCompact.page).toBe(1);
        expect(store.state.history.remote.filter.columnFilters).toEqual({
            resource: cleanEpisode,
            statusName: 'Downloaded',
            providerId: 'provider-a',
            quality: '1',
            size: '< 1024',
            clientStatus: 3
        });
        expect(store.state.history.remoteCompact.filter.columnFilters).toEqual({
            resource: cleanEpisode,
            statusName: 'Failed'
        });

        await store.dispatch('prepareHistoryLayoutTransition', { layout: 'compact' });

        expect(store.state.history.episodeFilter).toEqual({
            inputValue: cleanEpisode,
            filterValue: cleanEpisode,
            malformed: false,
            initialized: true
        });
        expect(store.state.history.remote.page).toBe(1);
        expect(store.state.history.remoteCompact.page).toBe(1);
        expect(store.state.history.remote.filter.columnFilters).toEqual({
            resource: cleanEpisode
        });
        expect(store.state.history.remoteCompact.filter.columnFilters).toEqual({
            resource: cleanEpisode
        });

        store.state.config.layout.history = 'compact';
        detailed.wrapper.destroy();

        const compact = mountHistoryComponent(HistoryCompact, store, cookieStore, {
            VueGoodTable: VueGoodTableStub,
            AppLink: true,
            QualityPill: true
        });
        expect(compact.wrapper.find('input[placeholder="Show title or release"]').element.value).toBe(cleanEpisode);
        compact.wrapper.destroy();

        await store.dispatch('prepareHistoryLayoutTransition', { layout: 'detailed' });
        expect(store.state.history.episodeFilter).toEqual({
            inputValue: cleanEpisode,
            filterValue: cleanEpisode,
            malformed: false,
            initialized: true
        });
        store.state.config.layout.history = 'detailed';

        const returnedDetailed = mountHistoryComponent(HistoryDetailed, store, cookieStore, {
            VueGoodTable: VueGoodTableStub,
            AppLink: true,
            QualityPill: true,
            FontAwesomeIcon: true,
            Multiselect: true
        });
        expect(returnedDetailed.wrapper.find('input[placeholder="Show title or release"]').element.value).toBe(cleanEpisode);
        expect(returnedDetailed.wrapper.find('input[placeholder="Provider | Group"]').element.value).toBe('');
        expect(returnedDetailed.wrapper.findAll('input').at(2).element.value).toBe('');
        expect(returnedDetailed.wrapper.vm.selectedClientStatusValue).toEqual([]);
        expect(store.state.history.remote.filter.columnFilters).toEqual({
            resource: cleanEpisode
        });
        returnedDetailed.wrapper.destroy();
    });

    it('canonicalizes malformed shared Episode values on Compact -> Detailed layout transition', async () => {
        const rawEpisode = '  "Compact route malformed';
        const cleanEpisode = 'Compact route malformed';
        const store = createHistoryStore({
            layout: 'compact',
            remote: {
                page: 4,
                filter: {
                    columnFilters: {
                        resource: 'detailed episode',
                        statusName: 'Downloaded',
                        providerId: 'provider-a',
                        quality: '1',
                        size: '< 1024',
                        clientStatus: 3
                    }
                }
            },
            remoteCompact: {
                page: 7,
                filter: {
                    columnFilters: {
                        resource: 'compact episode',
                        statusName: 'Failed'
                    }
                }
            }
        });
        const cookieStore = {};
        const compact = mountHistoryComponent(HistoryCompact, store, cookieStore, {
            VueGoodTable: VueGoodTableStub,
            AppLink: true,
            QualityPill: true
        });

        compact.wrapper.vm.updateResource({
            currentTarget: {
                value: rawEpisode
            }
        });
        await compact.wrapper.vm.$nextTick();

        expect(store.state.history.episodeFilter).toEqual({
            inputValue: rawEpisode,
            filterValue: cleanEpisode,
            malformed: true,
            initialized: true
        });
        expect(compact.wrapper.find('input[placeholder="Show title or release"]').element.value).toBe(rawEpisode);
        expect(store.state.history.remote.page).toBe(1);
        expect(store.state.history.remoteCompact.page).toBe(1);
        expect(store.state.history.remote.filter.columnFilters).toEqual({
            resource: cleanEpisode,
            statusName: 'Downloaded',
            providerId: 'provider-a',
            quality: '1',
            size: '< 1024',
            clientStatus: 3
        });
        expect(store.state.history.remoteCompact.filter.columnFilters).toEqual({
            resource: cleanEpisode,
            statusName: 'Failed'
        });

        await store.dispatch('prepareHistoryLayoutTransition', { layout: 'detailed' });

        expect(store.state.history.episodeFilter).toEqual({
            inputValue: cleanEpisode,
            filterValue: cleanEpisode,
            malformed: false,
            initialized: true
        });
        expect(store.state.history.remote.filter.columnFilters).toEqual({
            resource: cleanEpisode,
            statusName: 'Downloaded',
            providerId: 'provider-a',
            quality: '1',
            size: '< 1024',
            clientStatus: 3
        });
        expect(store.state.history.remoteCompact.filter.columnFilters).toEqual({
            resource: cleanEpisode,
            statusName: 'Failed'
        });
        compact.wrapper.destroy();

        store.state.config.layout.history = 'detailed';
        const detailed = mountHistoryComponent(HistoryDetailed, store, cookieStore, {
            VueGoodTable: VueGoodTableStub,
            AppLink: true,
            QualityPill: true,
            FontAwesomeIcon: true,
            Multiselect: true
        });
        expect(detailed.wrapper.find('input[placeholder="Show title or release"]').element.value).toBe(cleanEpisode);
        detailed.wrapper.destroy();
    });

    it.each([
        ['Detailed -> Compact', 'detailed', 'compact'],
        ['Compact -> Detailed', 'compact', 'detailed']
    ])('canonicalizes every empty Episode quote pair on %s layout changes', async (_name, fromLayout, toLayout) => {
        expect.hasAssertions();
        await Promise.all(matchingTextPairs.map(pair => assertEpisodePairLayoutReset({
            fromLayout,
            toLayout,
            pair
        })));
    });

    it('drops every pending Provider quote pair when leaving Detailed', async () => {
        expect.hasAssertions();
        await Promise.all(matchingTextPairs.map(pair => assertProviderPairLayoutReset(pair)));
    });

    it('keeps shared Episode edits and pending empty pairs in either layout', async () => {
        const store = createHistoryStore({
            layout: 'detailed',
            remote: {
                filter: {
                    columnFilters: {
                        resource: 'initial detailed'
                    }
                }
            },
            remoteCompact: {
                filter: {
                    columnFilters: {
                        resource: 'initial compact'
                    }
                }
            }
        });
        const cookieStore = {};
        const detailed = mountHistoryComponent(HistoryDetailed, store, cookieStore, {
            VueGoodTable: VueGoodTableStub,
            AppLink: true,
            QualityPill: true,
            FontAwesomeIcon: true,
            Multiselect: true
        });
        detailed.wrapper.vm.loadItemsDebounced.mockClear();
        detailed.wrapper.vm.updateResource({
            currentTarget: {
                value: '  "  Detailed title  "  '
            }
        });
        await detailed.wrapper.vm.$nextTick();
        expect(store.state.history.episodeFilter.filterValue).toBe('"  Detailed title  "');
        expect(store.state.history.remote.filter.columnFilters.resource).toBe('"  Detailed title  "');
        expect(store.state.history.remoteCompact.filter.columnFilters.resource).toBe('"  Detailed title  "');
        expect(detailed.wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);

        detailed.wrapper.vm.loadItemsDebounced.mockClear();
        detailed.wrapper.vm.updateResource({
            currentTarget: {
                value: '""'
            }
        });
        await detailed.wrapper.vm.$nextTick();
        expect(store.state.history.episodeFilter.inputValue).toBe('""');
        expect(store.state.history.episodeFilter.filterValue).toBe('');
        expect(store.state.history.episodeFilter.malformed).toBe(true);
        expect(store.state.history.remote.filter.columnFilters.resource).toBe('');
        expect(store.state.history.remoteCompact.filter.columnFilters.resource).toBe('');
        expect(detailed.wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        detailed.wrapper.destroy();

        store.state.config.layout.history = 'compact';
        const compact = mountHistoryComponent(HistoryCompact, store, cookieStore, {
            VueGoodTable: VueGoodTableStub,
            AppLink: true,
            QualityPill: true
        });
        compact.wrapper.vm.loadItemsDebounced.mockClear();
        compact.wrapper.vm.updateResource({
            currentTarget: {
                value: '  `  Compact title  `  '
            }
        });
        await compact.wrapper.vm.$nextTick();
        expect(store.state.history.episodeFilter.filterValue).toBe('`  Compact title  `');
        expect(store.state.history.remote.filter.columnFilters.resource).toBe('`  Compact title  `');
        expect(store.state.history.remoteCompact.filter.columnFilters.resource).toBe('`  Compact title  `');
        expect(compact.wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);

        compact.wrapper.vm.loadItemsDebounced.mockClear();
        compact.wrapper.vm.updateResource({
            currentTarget: {
                value: '``'
            }
        });
        await compact.wrapper.vm.$nextTick();
        expect(store.state.history.episodeFilter.inputValue).toBe('``');
        expect(store.state.history.episodeFilter.filterValue).toBe('');
        expect(store.state.history.episodeFilter.malformed).toBe(true);
        expect(store.state.history.remote.filter.columnFilters.resource).toBe('');
        expect(store.state.history.remoteCompact.filter.columnFilters.resource).toBe('');
        expect(compact.wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        compact.wrapper.destroy();
    });

    it('History parent transitions layouts and tracks active state', () => {
        const store = createHistoryStore({ layout: 'detailed' });
        const parent = makeMountedHistoryComponent(History);
        const wrapper = shallowMount(parent, {
            localVue: createLocalVueForHistory(),
            store,
            stubs: {
                HistoryDetailed: true,
                HistoryCompact: true,
                Backstretch: true
            }
        });
        expect(store.state.history.historyActive).toBe(true);

        const dispatch = jest.spyOn(store, 'dispatch');
        wrapper.vm.layout = 'compact';
        expect(dispatch.mock.calls.slice(-2)).toEqual([
            ['prepareHistoryLayoutTransition', { layout: 'compact' }],
            ['setLayout', { page: 'history', layout: 'compact' }]
        ]);
        expect(store.state.config.layout.history).toBe('compact');
        wrapper.destroy();
        expect(store.state.history.historyActive).toBe(false);
        dispatch.mockRestore();
    });

    it('cancels pending Detailed and Compact Episode debounces on destroy', () => {
        const detailed = mountDetailed();
        const detailedCancel = jest.fn();
        const detailedPending = jest.fn();
        detailedPending.cancel = detailedCancel;
        detailed.wrapper.vm.loadItemsDebounced = detailedPending;
        detailed.wrapper.destroy();
        expect(detailedCancel).toHaveBeenCalledTimes(1);

        const compact = mountCompact();
        const compactCancel = jest.fn();
        const compactPending = jest.fn();
        compactPending.cancel = compactCancel;
        compact.wrapper.vm.loadItemsDebounced = compactPending;
        compact.wrapper.destroy();
        expect(compactCancel).toHaveBeenCalledTimes(1);
    });

    it('loads Compact once with compact server parameters after restoring state', () => {
        const { wrapper, loadItems } = mountCompact({
            remoteCompact: {
                page: 3,
                perPage: 50,
                sort: [{ field: 'actionDate', type: 'asc' }],
                filter: {
                    columnFilters: {
                        resource: 'restored compact episode'
                    }
                }
            }
        });
        expect(loadItems).toHaveBeenCalledTimes(1);
        expect(loadItems.mock.results[0].value).toEqual(expect.objectContaining({
            page: 3,
            perPage: 50,
            compact: true,
            filter: {
                columnFilters: {
                    resource: 'restored compact episode'
                }
            }
        }));
        wrapper.destroy();
    });

    it('restores Detailed sort and pagination cookies before its one initial load', () => {
        const { wrapper, loadItems, setCookie, store } = mountDetailed({
            remote: {
                page: 3
            }
        }, {
            sort: [{ field: 'date', type: 'asc' }],
            'pagination-perpage-history': '50'
        });

        expect(loadItems).toHaveBeenCalledTimes(1);
        expect(loadItems.mock.results[0].value).toEqual(expect.objectContaining({
            page: 3,
            perPage: 50,
            sort: [{ field: 'actionDate', type: 'asc' }]
        }));
        expect(store.state.history.remote.perPage).toBe(50);
        expect(store.state.history.remote.sort).toEqual([{ field: 'actionDate', type: 'asc' }]);
        expect(setCookie).toHaveBeenCalledWith('sort', [{ field: 'actionDate', type: 'asc' }]);
        expect(setCookie).toHaveBeenCalledWith('pagination-perpage-history', 50);
        wrapper.destroy();
    });

    it('restores Compact sort and pagination cookies before its one initial load', () => {
        const { wrapper, loadItems, setCookie, store } = mountCompact({
            remoteCompact: {
                page: 4
            }
        }, {
            sort: [{ field: 'date', type: 'desc' }],
            'pagination-perpage-history': '100'
        });

        expect(loadItems).toHaveBeenCalledTimes(1);
        expect(loadItems.mock.results[0].value).toEqual(expect.objectContaining({
            page: 4,
            perPage: 100,
            sort: [{ field: 'actionDate', type: 'desc' }],
            compact: true
        }));
        expect(store.state.history.remoteCompact.perPage).toBe(100);
        expect(store.state.history.remoteCompact.sort).toEqual([{ field: 'actionDate', type: 'desc' }]);
        expect(setCookie).toHaveBeenCalledWith('sort', [{ field: 'actionDate', type: 'desc' }]);
        expect(setCookie).toHaveBeenCalledWith('pagination-perpage-history', 100);
        wrapper.destroy();
    });

    it.each([
        ['Detailed', {
            component: HistoryDetailed,
            remoteKey: 'remote',
            tableRef: 'detailed-history',
            stubs: {
                VueGoodTable: VueGoodTableStub,
                AppLink: true,
                QualityPill: true,
                FontAwesomeIcon: true,
                Multiselect: true
            }
        }],
        ['Compact', {
            component: HistoryCompact,
            remoteKey: 'remoteCompact',
            tableRef: 'compact-history',
            stubs: {
                VueGoodTable: VueGoodTableStub,
                AppLink: true,
                QualityPill: true
            }
        }]
    ])('restores the %s descending sort after VGT clears it', async (_name, options) => {
        const { component, remoteKey, tableRef, stubs } = options;
        const expectedSort = [{ field: 'actionDate', type: 'desc' }];
        const cookieStore = {
            sort: [{ field: 'quality', type: 'asc' }]
        };
        const store = createHistoryStore({
            layout: remoteKey === 'remote' ? 'detailed' : 'compact',
            [remoteKey]: {
                sort: [{ field: 'quality', type: 'asc' }]
            }
        });
        const mounted = mountHistoryComponent(component, store, cookieStore, stubs);
        const { wrapper, setCookie, loadItems } = mounted;
        const table = wrapper.vm.$refs[tableRef];
        const initializeSort = jest.spyOn(table, 'initializeSort');
        const actionDateColumn = wrapper.vm.columns.find(column => column.field === 'actionDate');
        const ascendingSort = [{ field: 'actionDate', type: 'asc' }];

        expect(actionDateColumn.firstSortType).toBe('desc');

        wrapper.vm.loadItemsDebounced.mockClear();
        table.emitSort([{ field: 'actionDate', type: 'none' }]);
        await wrapper.vm.$nextTick();

        expect(cookieStore.sort).toEqual(expectedSort);
        expect(setCookie).toHaveBeenCalledWith('sort', expectedSort);
        expect(store.state.history[remoteKey].sort).toEqual(expectedSort);
        expect(wrapper.vm.serverParams.sort).toEqual(expectedSort);
        expect(table.$props.sortOptions.initialSortBy).toEqual(expectedSort);
        expect(table.headerSort).toEqual(expectedSort);
        expect(initializeSort).toHaveBeenCalled();
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        expect(loadItems).toHaveBeenCalledTimes(1);

        initializeSort.mockClear();
        wrapper.vm.loadItemsDebounced.mockClear();
        table.emitSort(ascendingSort);
        await wrapper.vm.$nextTick();

        expect(cookieStore.sort).toEqual(ascendingSort);
        expect(setCookie).toHaveBeenLastCalledWith('sort', ascendingSort);
        expect(store.state.history[remoteKey].sort).toEqual(ascendingSort);
        expect(wrapper.vm.serverParams.sort).toEqual(ascendingSort);
        expect(initializeSort).not.toHaveBeenCalled();
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        wrapper.destroy();
    });

    it.each([
        ['active', [{ field: 'quality', type: 'asc' }]],
        ['clear-to-default', [{ field: 'actionDate', type: 'none' }]]
    ])('canonicalizes a malformed Detailed Episode filter on the %s sort', async (_name, sortEvent) => {
        const initialFilters = {
            resource: 'stored episode',
            providerId: 'provider-a',
            quality: '720p',
            size: '< 1024',
            clientStatus: 1,
            statusName: 'Downloaded'
        };
        const { wrapper, store } = mountDetailed({
            remote: {
                page: 4,
                filter: {
                    columnFilters: initialFilters
                }
            }
        });
        const table = wrapper.vm.$refs['detailed-history'];

        wrapper.vm.updateResource({
            currentTarget: {
                value: "'  malformed episode"
            }
        });
        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.remoteHistory.page = 4;
        store.state.history.remoteCompact.page = 7;

        table.emitSort(sortEvent);
        await wrapper.vm.$nextTick();

        expect(wrapper.find('input[placeholder="Show title or release"]').element.value).toBe('malformed episode');
        expect(store.state.history.episodeFilter).toEqual({
            inputValue: 'malformed episode',
            filterValue: 'malformed episode',
            malformed: false,
            initialized: true
        });
        expect(wrapper.vm.remoteHistory.filter.columnFilters).toEqual({
            ...initialFilters,
            resource: 'malformed episode'
        });
        expect(wrapper.vm.remoteHistory.page).toBe(4);
        expect(store.state.history.remoteCompact.page).toBe(7);
        expect(wrapper.vm.remoteHistory.sort).toEqual(sortEvent[0].type === 'none' ? [{
            field: 'actionDate',
            type: 'desc'
        }] : sortEvent);
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        wrapper.destroy();
    });

    it.each([
        ['active', [{ field: 'quality', type: 'asc' }]],
        ['clear-to-default', [{ field: 'actionDate', type: 'none' }]]
    ])('canonicalizes a malformed Detailed Provider filter on the %s sort', async (_name, sortEvent) => {
        const initialFilters = {
            resource: 'stored episode',
            providerId: 'stored provider',
            quality: '720p',
            size: '< 1024',
            clientStatus: 1,
            statusName: 'Downloaded'
        };
        const { wrapper, store } = mountDetailed({
            remote: {
                page: 4,
                filter: {
                    columnFilters: initialFilters
                }
            }
        });
        const table = wrapper.vm.$refs['detailed-history'];

        wrapper.vm.updateProvider({
            currentTarget: {
                value: "'  malformed provider"
            }
        });
        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.remoteHistory.page = 4;

        table.emitSort(sortEvent);
        await wrapper.vm.$nextTick();

        expect(wrapper.find('input[placeholder="Provider | Group"]').element.value).toBe('malformed provider');
        expect(wrapper.vm.providerFilterValue).toBe('malformed provider');
        expect(wrapper.vm.malformedTextFilters.providerId).toBe(false);
        expect(store.state.history.episodeFilter).toEqual({
            inputValue: 'stored episode',
            filterValue: 'stored episode',
            malformed: false,
            initialized: true
        });
        expect(wrapper.vm.remoteHistory.filter.columnFilters).toEqual({
            ...initialFilters,
            providerId: 'malformed provider'
        });
        expect(wrapper.vm.remoteHistory.page).toBe(4);
        expect(wrapper.vm.remoteHistory.sort).toEqual(sortEvent[0].type === 'none' ? [{
            field: 'actionDate',
            type: 'desc'
        }] : sortEvent);
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        wrapper.destroy();
    });

    it.each([
        ['active', [{ field: 'quality', type: 'asc' }]],
        ['clear-to-default', [{ field: 'actionDate', type: 'none' }]]
    ])('canonicalizes a malformed Compact Episode filter on the %s sort', async (_name, sortEvent) => {
        const initialFilters = {
            resource: 'stored compact episode',
            statusName: 'Downloaded',
            clientStatus: 1
        };
        const { wrapper, store } = mountCompact({
            remoteCompact: {
                page: 4,
                filter: {
                    columnFilters: initialFilters
                }
            }
        });
        const table = wrapper.vm.$refs['compact-history'];

        wrapper.vm.updateResource({
            currentTarget: {
                value: '  "  malformed compact episode'
            }
        });
        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.remoteHistory.page = 4;
        store.state.history.remote.page = 7;

        table.emitSort(sortEvent);
        await wrapper.vm.$nextTick();

        expect(wrapper.find('input[placeholder="Show title or release"]').element.value).toBe('malformed compact episode');
        expect(store.state.history.episodeFilter).toEqual({
            inputValue: 'malformed compact episode',
            filterValue: 'malformed compact episode',
            malformed: false,
            initialized: true
        });
        expect(wrapper.vm.remoteHistory.filter.columnFilters).toEqual({
            ...initialFilters,
            resource: 'malformed compact episode'
        });
        expect(wrapper.vm.remoteHistory.page).toBe(4);
        expect(store.state.history.remote.page).toBe(7);
        expect(wrapper.vm.remoteHistory.sort).toEqual(sortEvent[0].type === 'none' ? [{
            field: 'actionDate',
            type: 'desc'
        }] : sortEvent);
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        wrapper.destroy();
    });

    it.each([
        ['Detailed Episode active', 'detailed', 'resource', [{ field: 'quality', type: 'asc' }]],
        ['Detailed Episode clear-to-default', 'detailed', 'resource', [{ field: 'actionDate', type: 'none' }]],
        ['Detailed Provider active', 'detailed', 'providerId', [{ field: 'quality', type: 'asc' }]],
        ['Detailed Provider clear-to-default', 'detailed', 'providerId', [{ field: 'actionDate', type: 'none' }]],
        ['Compact Episode active', 'compact', 'resource', [{ field: 'quality', type: 'asc' }]],
        ['Compact Episode clear-to-default', 'compact', 'resource', [{ field: 'actionDate', type: 'none' }]]
    ])('canonicalizes every empty quote pair on %s sort', async (_name, layout, field, sortEvent) => {
        expect.hasAssertions();
        await Promise.all(matchingTextPairs.map(pair => assertHistoryPairSortReset({
            layout,
            field,
            pair,
            sortEvent
        })));
    });

    it.each([
        ['Date/Time', {
            firstSort: [{ field: 'date', type: 'asc' }],
            expectedSort: [{ field: 'actionDate', type: 'asc' }],
            compactStaleSort: [{ field: 'quality', type: 'desc' }],
            detailedStaleSort: [{ field: 'quality', type: 'desc' }]
        }],
        ['Quality', {
            firstSort: [{ field: 'quality', type: 'desc' }],
            expectedSort: [{ field: 'quality', type: 'desc' }],
            compactStaleSort: [{ field: 'date', type: 'asc' }],
            detailedStaleSort: [{ field: 'date', type: 'asc' }]
        }]
    ])('does not let stale %s cookies overwrite carried sort and pagination state', async (_name, sortCase) => {
        const store = createHistoryStore({
            layout: 'detailed',
            remote: {
                page: 4,
                perPage: 25,
                sort: [{ field: 'date', type: 'desc' }],
                filter: {
                    columnFilters: {
                        resource: 'carried episode'
                    }
                }
            },
            remoteCompact: {
                page: 6,
                perPage: 75,
                sort: [{ field: 'quality', type: 'asc' }],
                filter: {
                    columnFilters: {
                        resource: 'compact episode'
                    }
                }
            }
        });
        const detailed = mountHistoryComponent(HistoryDetailed, store, {
            sort: sortCase.firstSort,
            'pagination-perpage-history': '50'
        }, {
            VueGoodTable: VueGoodTableStub,
            AppLink: true,
            QualityPill: true,
            FontAwesomeIcon: true,
            Multiselect: true
        });
        expect(detailed.loadItems).toHaveBeenCalledTimes(1);
        detailed.wrapper.destroy();

        await store.dispatch('prepareHistoryLayoutTransition', { layout: 'compact' });
        store.state.config.layout.history = 'compact';
        const compact = mountHistoryComponent(HistoryCompact, store, {
            sort: sortCase.compactStaleSort,
            'pagination-perpage-history': '100'
        }, {
            VueGoodTable: VueGoodTableStub,
            AppLink: true,
            QualityPill: true
        });
        expect(compact.loadItems).toHaveBeenCalledTimes(1);
        expect(compact.loadItems.mock.results[0].value).toEqual(expect.objectContaining({
            perPage: 50,
            sort: sortCase.expectedSort,
            compact: true
        }));
        expect(store.state.history.remoteCompact.perPage).toBe(50);
        expect(store.state.history.remoteCompact.sort).toEqual(sortCase.expectedSort);
        expect(compact.setCookie).toHaveBeenCalledWith('sort', sortCase.expectedSort);
        expect(compact.setCookie).toHaveBeenCalledWith('pagination-perpage-history', 50);
        compact.wrapper.destroy();

        await store.dispatch('prepareHistoryLayoutTransition', { layout: 'detailed' });
        store.state.config.layout.history = 'detailed';
        const returnedDetailed = mountHistoryComponent(HistoryDetailed, store, {
            sort: sortCase.detailedStaleSort,
            'pagination-perpage-history': '75'
        }, {
            VueGoodTable: VueGoodTableStub,
            AppLink: true,
            QualityPill: true,
            FontAwesomeIcon: true,
            Multiselect: true
        });
        expect(returnedDetailed.loadItems).toHaveBeenCalledTimes(1);
        expect(returnedDetailed.loadItems.mock.results[0].value).toEqual(expect.objectContaining({
            perPage: 50,
            sort: sortCase.expectedSort
        }));
        expect(store.state.history.remote.perPage).toBe(50);
        expect(store.state.history.remote.sort).toEqual(sortCase.expectedSort);
        expect(returnedDetailed.setCookie).toHaveBeenCalledWith('sort', sortCase.expectedSort);
        expect(returnedDetailed.setCookie).toHaveBeenCalledWith('pagination-perpage-history', 50);
        returnedDetailed.wrapper.destroy();
    });

    it('compact pager options track page and remain on first page when episode/resource filter is set and cleared', async () => {
        const { wrapper } = mountCompact({
            remoteCompact: {
                page: 6,
                filter: {
                    columnFilters: {
                        resource: 'compact show',
                        statusName: 'Downloaded',
                        clientStatus: 5
                    }
                }
            }
        });

        wrapper.vm.loadItemsDebounced.mockClear();

        expect(getPaginationOptions(wrapper).setCurrentPage).toBe(6);

        wrapper.vm.onPageChange({
            currentPage: 3
        });
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.remoteHistory.page).toBe(3);
        expect(getPaginationOptions(wrapper).setCurrentPage).toBe(3);
        wrapper.vm.loadItemsDebounced.mockClear();

        wrapper.vm.updateResource({
            currentTarget: {
                value: 'new compact resource'
            }
        });
        expect(wrapper.vm.remoteHistory.page).toBe(1);
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        await wrapper.vm.$nextTick();
        expect(getPaginationOptions(wrapper).setCurrentPage).toBe(1);

        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.updateResource({
            currentTarget: {
                value: ''
            }
        });
        expect(wrapper.vm.remoteHistory.page).toBe(1);
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        await wrapper.vm.$nextTick();
        expect(getPaginationOptions(wrapper).setCurrentPage).toBe(1);
        wrapper.destroy();
    });

    it('both components render the Episode filter placeholder as Show title or release', () => {
        const { wrapper: detailed } = mountDetailed();
        const { wrapper: compact } = mountCompact();

        expect(detailed.find('input[placeholder="Show title or release"]').exists()).toBe(true);
        expect(compact.find('input[placeholder="Show title or release"]').exists()).toBe(true);
        detailed.destroy();
        compact.destroy();
    });

    it('detailed Size filter placeholder uses an unquoted example', () => {
        const { wrapper } = mountDetailed();

        const sizeInput = wrapper.findAll('input').at(2);
        expect(sizeInput.attributes('placeholder')).toBe('e.g. <200 MB or >1.3 GB');
        expect(sizeInput.attributes('placeholder')).not.toContain('`');
        wrapper.destroy();
    });
});
