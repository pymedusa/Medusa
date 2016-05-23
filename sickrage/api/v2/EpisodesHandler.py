class EpisodeHandler():
    def get(self, recipe_id=[]):
        if recipe_id == []:
            # Handle me
            self.set_status(400)
            return self.finish("Invalid recipe id")
        return ({
            "recipe_id": recipe_id
        })
