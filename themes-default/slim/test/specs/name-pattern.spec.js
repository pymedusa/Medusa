import test from 'ava';
import { createLocalVue, mount } from '@vue/test-utils';

// Needs to be required otherwise nyc won't see it
const NamePattern = require('../../static/js/templates/name-pattern.vue');

test.beforeEach(t => {
    t.context.localVue = createLocalVue();
});

test('renders', t => {
    const { localVue } = t.context;
    const wrapper = mount(NamePattern, {
        localVue,
        propsData: {
            namingPattern: 'S%0SE%0E - %EN',
            namingPresets: [
                '%SN - %Sx%0E - %EN',
                '%S.N.S%0SE%0E.%E.N',
                '%Sx%0E - %EN',
                'S%0SE%0E - %EN',
                'Season %0S/%S.N.S%0SE%0E.%Q.N-%RG'
            ],
            type: '',
            multiEpStyle: 1,
            animeNamingType: 0
        },
        methods: {
            checkNaming(pattern, selectedMultiEpStyle, animeType) {
                console.debug(`Mocking method checkNaming with params: ${pattern}, ${selectedMultiEpStyle} and ${animeType}`);
            },
            testNaming(pattern, selectedMultiEpStyle, animeType) {
                console.debug(`Mocking method testNaming with params: ${pattern}, ${selectedMultiEpStyle} and ${animeType}`);
            }
        }
    });

    t.snapshot(wrapper.html());
});
