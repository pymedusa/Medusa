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
     * @param {localVue} localVue property.
     * @param {store} store property.
     * @param {string} message - Test message.
     * @param {object} propsData - Props to pass to the component.
     */
    const propTest = (localVue, store, message, propsData) => {
        expect(mount(component, {
            localVue,
            store,
            propsData
        }).element).toMatchSnapshot(message);
    };

    return propTest;
};

export {
    generatePropTest
};
