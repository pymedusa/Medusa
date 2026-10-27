<template>
    <div class="table-page-size footer__row-count">
        <label class="footer__row-count__label">
            Rows per page:
            <select name="perPageSelect" class="footer__row-count__select" aria-label="Rows per page"
                    :value="value" @change="$emit('input', Number($event.target.value))">
                <option v-for="size in options" :key="size" :value="size">{{size}}</option>
                <option :value="-1">All</option>
            </select>
        </label>
    </div>
</template>

<script>
export const formatPaginationInfo = (info, perPage) => {
    const { firstRecordOnPage, lastRecordOnPage, totalRecords } = info;
    const first = totalRecords === 0 ? 0 : (perPage === -1 ? 1 : firstRecordOnPage);
    const last = perPage === -1 ? totalRecords : lastRecordOnPage;
    return `${first} - ${last} of ${totalRecords}`;
};

export default {
    name: 'table-page-size',
    props: {
        value: { type: Number, required: true },
        options: { type: Array, required: true }
    }
};
</script>

<style scoped>
.table-page-size {
    padding: 0.6em 1em;
}

label {
    display: inline-flex;
    align-items: center;
    margin: 0;
}

select {
    margin-left: 8px;
}
</style>
