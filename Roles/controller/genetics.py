'''Ported from Dan Shiffman's Nature of Code:
https://github.com/shiffman/The-Nature-of-Code-Examples-p5.js/tree/master/chp09_ga/NOC_9_01_GA_Shakespeare_simplified
Thanks Dan!!
'''

import label_image
import random
import json

# possible values for the genome
# if you add any new DMX stuff, change here AND in Roles/client/main.py
DMX_VALUE_RANGES = {
    "mister_1":     [0,255],
    "mister_2":     [0,255],
    "grow_light":   [0,255],
    "pump":         [0,255],
    "raindrops_1":  [0,255],
    "raindrops_2":  [0,255],
    "raindrops_3":  [0,255],
    "dj_light_1_d": [255],
    "dj_light_1_r": range(0,255),
    "dj_light_1_g": range(0,255),
    "dj_light_1_b": range(0,255),
    "dj_light_2_d": [255],
    "dj_light_2_r": range(0,255),
    "dj_light_2_g": range(0,255),
    "dj_light_2_b": range(0,255),
     "dj_light_3_r": range(0,255),
    "dj_light_3_g": range(0,255),
    "dj_light_3_b": range(0,255),
}

def remap(value, source_range, target_range):
    ''' remaps a value from a source range to a target range
    modified from p5py
    '''

    s0, s1 = source_range
    t0, t1 = target_range
    S = s1 - s0
    T = t1 - t0
    return float(t0) + ((float(value) - float(s0)) / float(S)) * float(T)


class DNA(object):
    def __init__(self, fitness_label):
        self.fitness = 0
        self.image = None
        self.fitness_label = fitness_label
        self.genes = self.random_genome()

    def random_gene(self, dmx_name):
        '''generates a random gene based on dmx ranges'''
        return random.choice(DMX_VALUE_RANGES[dmx_name])

    def random_genome(self):
        '''generates a fully random genome'''
        out = {}
        for key in DMX_VALUE_RANGES:
            out[key] = self.random_gene(key)
        return out

    def get_phrase(self):
        return self.genes

    def calculate_fitness(self):
        scores = label_image.label(self.image)
        scores = dict(scores)
        print scores
        self.fitness = scores.get(self.fitness_label, 0)
        return self.fitness

    def crossover(self, partner):
        child = DNA(self.fitness_label)
        midpoint = random.randint(0, len(self.genes.keys()))

        for i, k in enumerate(self.genes):
            if i > midpoint:
                child.genes[k] = self.genes[k]
            else:
                child.genes[k] = partner.genes[k]
        return child

    def mutate(self, mutation_rate):
        for k in self.genes:
            if random.random() < mutation_rate:
                self.genes[k] = self.random_gene(k)


class Population(object):
    def __init__(self, fitness_label, mutation_rate=0.01, pop_max=10):
        self.mating_pool = []
        self.generations = 0
        self.finished = False
        self.target = 0.9
        self.mutation_rate = mutation_rate
        self.finished_thresh = 0.95
        self.fitness_label = fitness_label
        self.pop_max = pop_max
        self.best = ''
        self.current_dna = 0

        self.population = [DNA(fitness_label) for i in range(0, pop_max)]
        # self.calculate_fitness()

    def calculate_current_fitness(self, filename):
        self.population[self.current_dna].image = filename
        self.population[self.current_dna].calculate_fitness()

    def get_current_state(self):
        return self.population[self.current_dna].genes

    def natural_selection(self):
        self.mating_pool = []
        max_fitness = max([p.fitness for p in self.population])

        for p in self.population:
            fitness = remap(p.fitness, (0, max_fitness), (0, 1))
            n = int(fitness * 100)
            self.mating_pool += [p] * n

    def generate(self):
        new_pop = []
        for p in self.population:
            partner_a = random.choice(self.mating_pool)
            partner_b = random.choice(self.mating_pool)
            child = partner_a.crossover(partner_b)
            child.mutate(self.mutation_rate)
            new_pop.append(child)
        self.population = new_pop
        self.generations += 1

    def get_best(self):
        return self.best

    def evaluate(self):
        index = 0
        max_fitness = 0

        self.best = sorted([p for p in self.population], key=lambda k: k.fitness)[-1]
        if self.best.fitness >= self.finished_thresh:
            self.finished = True

    def get_average_fitness(self):
        total = sum([p.fitness for p in self.population])
        return float(total) / float(len(self.population))

    def to_dict(self):
        pop = [{'image': p.image, 'fitness': p.fitness, 'genes': p.genes} for p in self.population]

        out = {
            'generations': self.generations,
            'finished': self.finished,
            'mutation_rate': self.mutation_rate,
            'finished_thresh': self.finished_thresh,
            'fitness_label': self.fitness_label,
            'pop_max': self.pop_max,
            'current_dna': self.current_dna,
            'population': pop
        }



if __name__ == '__main__':
    wetland = Population('wetlands landscape', 0.01, 100)
    for i in range(0, 800):
        if wetland.current_dna < len(wetland.population) - 1:
            wetland.calculate_current_fitness('test.png')
            wetland.current_dna += 1
        else:
            wetland.natural_selection()
            wetland.generate()
            wetland.evaluate()
            wetland.current_dna = 0

        next_env_state = wetland.get_current_state()
        print next_env_state

