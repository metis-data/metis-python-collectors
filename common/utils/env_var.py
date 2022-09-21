import os

from common.utils.log import log

METIS_TAGS_PREFIX = "METIS_TAG"


@log
def extract_additional_tags_from_env_var():
    env_tags = [env_var for env_var in os.environ.items()
                if env_var[0].startswith(METIS_TAGS_PREFIX)]
    tags = {}
    if len(env_tags) > 0:
        # extract name
        import re
        compiled_regex = re.compile(rf'{METIS_TAGS_PREFIX}_(\w+)?')
        for metis_tag_item in env_tags:
            tag_name = compiled_regex.findall(metis_tag_item[0])
            if tag_name:
                tags[tag_name[0].strip().lower()] = metis_tag_item[1].strip()

    return tags
