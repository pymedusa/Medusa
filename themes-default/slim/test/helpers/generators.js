import { mount } from '@vue/test-utils';

/**
 * Generate a simple component prop test case.
 *
 * @param {*} component - A Vue component.
 * @returns {propTest} Test case function.
 */
const generatePropTest = component => {
    /**
     * A simple component prop test case.
     *
     * @param {*} t - AVA test with a context containing `localVue` and `store` properties.
     * @param {string} message - Test message.
     * @param {object} propsData - Props to pass to the component.
     */
    const propTest = (t, message, propsData) => {
        const { localVue, store } = t.context;

        t.snapshot(mount(component, {
            localVue,
            store,
            propsData
        }).html(), message);
    };
    return propTest;
};

export {
    generatePropTest
};
