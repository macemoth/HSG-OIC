import os
import subprocess
import time

import matplotlib.pyplot as plt

from cam import Camera

import json

class Graphene():

    def __init__(self):
        self.triples = set()
        self.addQueue = set()
        self.graph_path = "graph.json"
        self.img_path = "snap.png"
        self.camera = None


    def run(self):
        self.camera = Camera(device=0, preview=False, threshold=5, export_path=self.img_path)
        while(True):
            self.update()

    def update(self):
        # Get image (once the camera returns, we know there was movement, everything is synchronous)
        self.camera.run()
        print("--------------------")
        print("Change detected. Generating graph...")

        # Call scene graph generator
        self.generate_scene_graph("RelTR", self.img_path, self.graph_path)
        new_triples, dropped_triples, read_triples = self.read_triples_diff(self.graph_path)

        # TODO: make better output
        for drop in dropped_triples:
            print(f"{drop.object} {drop.predicate} {drop.subject} has dropped out." )

        for new in new_triples:
            print(f"{new.subject} {new.predicate} {new.object} has popped up.")
            # self.addQueue.add(new)

        self.triples = read_triples # currently, we show everything detected
        self.visualise(self.img_path)

    def generate_scene_graph(self, reltr_path, img_path, graph_path, device="cpu", topk=5):
        subprocess.check_output([f'python',
                                 f"{reltr_path}/mkgraph.py",
                                 "--img_path", f"{img_path}",
                                 "--device", f"{device}",
                                 "--resume", f"{reltr_path}/ckpt/checkpoint0149.pth",
                                 "--export_path", f"{graph_path}",
                                 "--topk", f"{topk}"])

    def read_triples_diff(self, graph_path):
        """
        Complete import of a graph.
        """
        triples_read = set()
        with open(graph_path, "r") as file:
            triples = json.load(file)
            file.close()

        for triple_dict in triples:
            subject = triple_dict["subject"]
            predicate = triple_dict["predicate"]
            object = triple_dict["object"]
            triple = Triple(subject["id"], predicate["id"], object["id"])
            triple.setSubjectBox(subject["xmin"], subject["ymin"], subject["xmax"], subject["ymax"])
            triple.setObjectBox(object["xmin"], object["ymin"], object["xmax"], object["ymax"])
            triples_read.add(triple)

        new_triples = triples_read - self.triples
        dropped_triples = self.triples - triples_read

        return new_triples, dropped_triples, triples_read

    def visualise(self, img_path):
        fig, ax = plt.subplots()
        im = plt.imread(img_path)
        ax.imshow(im)
        for triple in self.triples:
            (oxmin, oymin, oxmax, oymax) = triple.obox
            (sxmin, symin, sxmax, symax) = triple.sbox
            oxcentre = oxmin + (oxmax-oxmin)/2
            oycentre = oymin + (oymax-oymin)/2
            sxcentre = sxmin + (sxmax-sxmin)/2
            sycentre = symin + (symax-symin)/2
            xlinecentre = oxcentre + (sxcentre-oxcentre)/2
            ylinecentre = oycentre + (sycentre-oycentre)/2
            ax.add_patch(plt.Rectangle((sxmin, symin), sxmax - sxmin, symax - symin,
                                    fill=False, color='blue', linewidth=2.5))
            ax.add_patch(plt.Rectangle((oxmin, oymin), oxmax - oxmin, oymax - oymin,
                                    fill=False, color='orange', linewidth=2.5))
            ax.annotate(triple.subject, (sxmin, symin), color="white")
            ax.annotate(triple.object, (oxmin, oymin), color="white")
            #ax.add_patch(plt.Arrow((sxcentre, sycentre), (oxcentre, oycentre), color="red"))
            ax.annotate(triple.predicate, (xlinecentre, ylinecentre), color="white")
        plt.show(block=False)
        plt.show()

class Triple():

    def __init__(self, subject, predicate, object):
        self.subject = subject
        self.predicate = predicate
        self.object = object

    def __hash__(self):
        """Should only check on S, P, O, but not other variables"""
        return hash((self.subject, self.predicate, self.object))

    def setObjectBox(self, oxmin, oymin, oxmax, oymax):
        self.obox = (oxmin, oymin, oxmax, oymax)

    def setSubjectBox(self, sxmin, symin, sxmax, symax):
        self.sbox = (sxmin, symin, sxmax, symax)


if __name__ == "__main__":
    os.environ['MKL_THREADING_LAYER'] = 'GNU'
    graphene = Graphene()
    graphene.run()
