import pokebase as pb

# Test with a Pokémon
pokemon = pb.pokemon('pikachu')

# Print basic information
print(f"Name: {pokemon.name}")
print(f"ID: {pokemon.id}")
print(f"Height: {pokemon.height}")
print(f"Weight: {pokemon.weight}")
print(f"Base Experience: {pokemon.base_experience}")

# Print types
print("Types:")
for type_slot in pokemon.types:
    print(f"- {type_slot.type.name}")

# Print abilities
print("Abilities:")
for ability_slot in pokemon.abilities:
    print(f"- {ability_slot.ability.name} ({'Hidden' if ability_slot.is_hidden else 'Normal'})")

# Print stats
print("Stats:")
for stat in pokemon.stats:
    print(f"- {stat.stat.name}: {stat.base_stat}")

# Get species information
species = pokemon.species
print(f"Species: {species.name}")
print(f"Generation: {species.generation.name}")
print(f"Capture Rate: {species.capture_rate}")
print(f"Base Happiness: {species.base_happiness}")
print(f"Growth Rate: {species.growth_rate.name}")

# Get color and habitat if available
if hasattr(species, 'color'):
    print(f"Color: {species.color.name}")
if hasattr(species, 'habitat'):
    print(f"Habitat: {species.habitat.name if species.habitat else 'None'}") 